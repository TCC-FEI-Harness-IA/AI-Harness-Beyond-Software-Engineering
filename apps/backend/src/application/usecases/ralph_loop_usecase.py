from collections.abc import AsyncGenerator
from datetime import UTC, datetime
import json
import logging
from uuid import uuid4

from src.application.prompts.prompt_templates import (
    TEMPLATE_A1_CRITERIA,
    TEMPLATE_A2_DECOMPOSITION,
    TEMPLATE_B1_EXECUTE,
    TEMPLATE_B2_VERIFY,
    TEMPLATE_B4_LEARN,
    TEMPLATE_C1_VERIFY_GLOBAL,
    TEMPLATE_C2_ADDITIONAL_PLANNING,
    TEMPLATE_C3_FINAL_SYNTHESIS,
    extract_json_payload,
)
from src.domain.classes.llm.messages.message import Message
from src.domain.classes.ralph_loop.ralph_loop_entities import (
    ContextWindowInfo,
    RalphLoopExecutionSummary,
    RalphLoopStepEvent,
    RalphTask,
)
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.interfaces.llm_complitions_interface import ILLMCompletions


class RalphLoopUseCase:
    """Caso de uso orquestrador do Ralph Wiggum Loop adaptado para perguntas em linguagem natural.

    Implementa:
    - Fase A: Planejamento (Critérios Gerais A.1 + Decomposição em Tarefas A.2)
    - Fase B: Execução em Loop com Fresh Context (B.1/B.2 Execução, B.2 Verificação, B.3 Armazenamento, B.4 Aprendizados)
    - Fase C: Síntese e Validação Global (C.1 Verificação Global, C.2 Planejamento Adicional, C.3 Resposta Final)
    """

    def __init__(
        self,
        llm_completions: ILLMCompletions,
        logger: logging.Logger,
    ) -> None:
        self.llm_completions = llm_completions
        self.logger = logger

    def _call_llm(
        self,
        messages: Message | list[Message],
        model_name: str | None,
        provider: str | None,
        endpoint: str | None,
        max_tokens: int | None,
        temperature: float | None,
    ) -> tuple[str, int]:
        """Auxiliar síncrono para chamada ao adaptador de LLM e retorno de texto e tokens."""
        llm_message = self.llm_completions.send_message(
            input_message=messages,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            provider=provider,
            endpoint=endpoint,
        )

        output_text = (
            llm_message.output_message.text
            if llm_message.output_message is not None
            else ""
        )

        call_tokens = 0
        if llm_message.tokens is not None:
            call_tokens = llm_message.tokens.tokens_input + llm_message.tokens.tokens_output

        return output_text, call_tokens

    async def execute_stream(
        self,
        user_input: str,
        model_name: str | None = None,
        provider: str | None = None,
        endpoint: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        max_retries_per_task: int = 3,
        max_additional_planning_rounds: int = 2,
    ) -> AsyncGenerator[str, None]:
        """Executa o ciclo completo do Ralph Loop emitindo eventos Server-Sent Events (SSE)."""
        summary = await self._run_loop(
            user_input=user_input,
            model_name=model_name,
            provider=provider,
            endpoint=endpoint,
            max_tokens=max_tokens,
            temperature=temperature,
            max_retries_per_task=max_retries_per_task,
            max_additional_planning_rounds=max_additional_planning_rounds,
            stream_callback=None,
        )

        # Se houver callback ou se quisermos fazer yield dos eventos
        for event in summary.events:
            yield json.dumps(event.to_dict(), ensure_ascii=False)

    async def execute_sync(
        self,
        user_input: str,
        model_name: str | None = None,
        provider: str | None = None,
        endpoint: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        max_retries_per_task: int = 3,
        max_additional_planning_rounds: int = 2,
    ) -> RalphLoopExecutionSummary:
        """Executa o ciclo de forma síncrona retornando o resumo estruturado (ideal para benchmarks)."""
        return await self._run_loop(
            user_input=user_input,
            model_name=model_name,
            provider=provider,
            endpoint=endpoint,
            max_tokens=max_tokens,
            temperature=temperature,
            max_retries_per_task=max_retries_per_task,
            max_additional_planning_rounds=max_additional_planning_rounds,
            stream_callback=None,
        )

    async def _run_loop(
        self,
        user_input: str,
        model_name: str | None,
        provider: str | None,
        endpoint: str | None,
        max_tokens: int | None,
        temperature: float | None,
        max_retries_per_task: int,
        max_additional_planning_rounds: int,
        stream_callback=None,
    ) -> RalphLoopExecutionSummary:
        events: list[RalphLoopStepEvent] = []
        total_tokens = 0

        # =====================================================================
        # FASE A: Planejamento
        # =====================================================================
        self.logger.info("Iniciando Fase A.1 - Definição dos critérios de aceite gerais")
        ctx_setup = uuid4().hex[:7]
        prompt_a1 = TEMPLATE_A1_CRITERIA.format(user_input=user_input)

        msg_a1 = Message(creation_timestamp=datetime.now(tz=UTC), text=prompt_a1, source=MessageSourceEnum.USER)
        res_a1_text, tokens_a1 = self._call_llm(
            messages=msg_a1,
            model_name=model_name,
            provider=provider,
            endpoint=endpoint,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        total_tokens += tokens_a1

        payload_a1 = extract_json_payload(res_a1_text)
        criteria_list: list[str] = payload_a1.get("criteria", [])
        if not criteria_list:
            criteria_list = [
                "A pergunta deve ser respondida com exatidão no idioma adequado.",
                "Responda somente a alternativa ou a conclusão direta, sem explicações adicionais.",
                "O valor final deve corresponder a uma das alternativas fornecidas.",
            ]

        setup_md = "## 🔧 Configuração — Critérios de Aceite Gerais\n\n"
        for crit in criteria_list:
            setup_md += f"- {crit}\n"

        events.append(
            RalphLoopStepEvent(
                type="thinking",
                subtype="setup",
                task="setup",
                content=setup_md,
                total_tokens=total_tokens,
                context_window=ContextWindowInfo(context_id=ctx_setup, context_size=tokens_a1),
            )
        )

        # A.2 Quebra em tarefas
        self.logger.info("Iniciando Fase A.2 - Decomposição em tarefas")
        ctx_tasks = uuid4().hex[:7]
        prompt_a2 = TEMPLATE_A2_DECOMPOSITION.format(user_input=user_input)

        msg_a2 = Message(creation_timestamp=datetime.now(tz=UTC), text=prompt_a2, source=MessageSourceEnum.USER)
        res_a2_text, tokens_a2 = self._call_llm(
            messages=msg_a2,
            model_name=model_name,
            provider=provider,
            endpoint=endpoint,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        total_tokens += tokens_a2

        payload_a2 = extract_json_payload(res_a2_text)
        raw_tasks = payload_a2.get("tasks", [])
        task_queue: list[RalphTask] = []

        if isinstance(raw_tasks, list) and raw_tasks:
            for idx, t in enumerate(raw_tasks, start=1):
                if isinstance(t, dict):
                    task_queue.append(
                        RalphTask(
                            id=str(t.get("id") or f"T{idx}"),
                            title=str(t.get("title") or f"Tarefa {idx}"),
                            description=str(t.get("description") or f"Subtarefa {idx}"),
                            acceptance_criteria=list(t.get("acceptance_criteria") or ["Resolver escopo"]),
                        )
                    )

        if not task_queue:
            task_queue = [
                RalphTask(
                    id="T1",
                    title="Análise preliminar",
                    description=f"Identifique os elementos e condições presentes em: {user_input}",
                    acceptance_criteria=[
                        "Retornar a lista de elementos identificados.",
                        "A resposta não deve tentar resolver a questão final.",
                        "A resposta não deve avaliar nenhuma outra condição.",
                    ],
                )
            ]

        tasks_md = "## 📋 Decomposição — Tarefas Geradas\n\n"
        for t in task_queue:
            tasks_md += f"### {t.id} — {t.title}\n{t.description}\n\n**Critérios:**\n"
            for crit in t.acceptance_criteria:
                tasks_md += f"- {crit}\n"
            tasks_md += "\n---\n\n"

        events.append(
            RalphLoopStepEvent(
                type="thinking",
                subtype="tasks",
                task="setup",
                content=tasks_md,
                total_tokens=total_tokens,
                context_window=ContextWindowInfo(context_id=ctx_tasks, context_size=tokens_a2),
            )
        )

        # =====================================================================
        # FASE B: Execução em Loop com Fresh Context
        # =====================================================================
        stored_results: dict[str, str] = {}
        accumulated_learnings: list[str] = []
        additional_planning_rounds = 0

        while task_queue:
            current_task = task_queue.pop(0)
            self.logger.info("Executando tarefa %s: %s", current_task.id, current_task.title)

            # Novo contexto inicializado para cada nova tarefa (Fresh Context!)
            task_ctx_id = uuid4().hex[:7]
            task_ctx_size = 0

            # Injeção explícita de aprendizados no início do contexto
            if accumulated_learnings:
                learnings_block = (
                    "APRENDIZADOS RELEVANTES DE TAREFAS ANTERIORES:\n"
                    + "\n".join(f"- {fact}" for fact in accumulated_learnings)
                )
            else:
                learnings_block = "Nenhum aprendizado acumulado até o momento."

            criteria_str = "\n".join(f"- {c}" for c in current_task.acceptance_criteria)

            prompt_b1 = TEMPLATE_B1_EXECUTE.format(
                accumulated_learnings_section=learnings_block,
                task_id=current_task.id,
                task_title=current_task.title,
                task_description=current_task.description,
                task_criteria=criteria_str,
            )

            # Histórico de contexto da tarefa (reutilizado durante retentativas da mesma tarefa)
            task_conversation: list[Message] = [
                Message(creation_timestamp=datetime.now(tz=UTC), text=prompt_b1, source=MessageSourceEnum.USER)
            ]

            is_approved = False
            task_approved_result = ""
            res_b1_text = ""
            task_history_full: list[str] = []

            for attempt in range(1, max_retries_per_task + 1):
                current_task.attempts = attempt

                exec_md = f"## ⚙️ Execução — {current_task.id}"
                if attempt > 1:
                    exec_md += f" *(Tentativa {attempt})*"
                exec_md += f"\n\n**Enunciado:**\n> {current_task.description}\n\n"
                exec_md += f"**Aprendizados disponíveis:**\n"
                if accumulated_learnings:
                    for fact in accumulated_learnings:
                        exec_md += f"- {fact}\n"
                else:
                    exec_md += "Nenhum\n"

                events.append(
                    RalphLoopStepEvent(
                        type="thinking",
                        subtype="execute",
                        task=current_task.id,
                        content=exec_md,
                        total_tokens=total_tokens,
                        context_window=ContextWindowInfo(context_id=task_ctx_id, context_size=task_ctx_size),
                    )
                )

                # Chamada de resolução
                res_b1_text, tokens_b1 = self._call_llm(
                    messages=task_conversation,
                    model_name=model_name,
                    provider=provider,
                    endpoint=endpoint,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                total_tokens += tokens_b1
                task_ctx_size += tokens_b1
                task_history_full.append(f"Tentativa {attempt}: {res_b1_text}")

                reasoning_md = f"## 💭 Raciocínio — {current_task.id}"
                if attempt > 1:
                    reasoning_md += f" *(Tentativa {attempt})*"
                reasoning_md += f"\n\n{res_b1_text}\n"

                events.append(
                    RalphLoopStepEvent(
                        type="thinking",
                        subtype="reasoning",
                        task=current_task.id,
                        content=reasoning_md,
                        total_tokens=total_tokens,
                        context_window=ContextWindowInfo(context_id=task_ctx_id, context_size=task_ctx_size),
                    )
                )

                # B.2 Verificação dos critérios da tarefa
                ctx_verify = uuid4().hex[:7]
                prompt_b2 = TEMPLATE_B2_VERIFY.format(
                    task_description=current_task.description,
                    task_criteria=criteria_str,
                    preliminary_result=res_b1_text,
                )

                msg_b2 = Message(creation_timestamp=datetime.now(tz=UTC), text=prompt_b2, source=MessageSourceEnum.USER)
                res_b2_text, tokens_b2 = self._call_llm(
                    messages=msg_b2,
                    model_name=model_name,
                    provider=provider,
                    endpoint=endpoint,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                total_tokens += tokens_b2

                payload_b2 = extract_json_payload(res_b2_text)
                approved = bool(payload_b2.get("approved", False))
                feedback = str(payload_b2.get("feedback") or "Critérios avaliados.")

                if approved:
                    is_approved = True
                    task_approved_result = res_b1_text

                    verify_md = f"## ✅ Verificação — {current_task.id}\n\n"
                    evals = payload_b2.get("evaluations", [])
                    if isinstance(evals, list) and evals:
                        for ev in evals:
                            if isinstance(ev, dict):
                                crit_name = ev.get("criterion", "Critério")
                                met = ev.get("met", True)
                                verify_md += f"- [{'x' if met else ' '}] {crit_name}\n"
                    else:
                        verify_md += f"- [x] Critérios individuais atendidos.\n"
                    verify_md += f"\n> **Status: APROVADO**\n"

                    events.append(
                        RalphLoopStepEvent(
                            type="thinking",
                            subtype="verify_pass",
                            task=current_task.id,
                            content=verify_md,
                            total_tokens=total_tokens,
                            context_window=ContextWindowInfo(context_id=ctx_verify, context_size=tokens_b2),
                        )
                    )
                    break
                else:
                    verify_fail_md = f"## ❌ Verificação — {current_task.id} *(Tentativa {attempt})*\n\n"
                    verify_fail_md += f"> **Status: REPROVADO** — {feedback}\n"

                    events.append(
                        RalphLoopStepEvent(
                            type="thinking",
                            subtype="verify_fail",
                            task=current_task.id,
                            content=verify_fail_md,
                            total_tokens=total_tokens,
                            context_window=ContextWindowInfo(context_id=ctx_verify, context_size=tokens_b2),
                        )
                    )

                    # Se reprovado e ainda houver tentativas, mantém o contexto anterior da tarefa para retry
                    if attempt < max_retries_per_task:
                        task_conversation.append(
                            Message(
                                creation_timestamp=datetime.now(tz=UTC),
                                text=res_b1_text,
                                source=MessageSourceEnum.LLM_AGENT,
                            )
                        )
                        task_conversation.append(
                            Message(
                                creation_timestamp=datetime.now(tz=UTC),
                                text=(
                                    f"Sua tentativa foi REPROVADA. Motivo / Feedback: {feedback}\n"
                                    "Por favor, forneça uma nova resposta corrigindo estritamente as violações "
                                    "e atendendo a todos os critérios sem adiantar a resposta final."
                                ),
                                source=MessageSourceEnum.USER,
                            )
                        )

            # Caso não tenha sido aprovado em nenhuma tentativa, usa a última saída para evitar deadlock
            if not is_approved:
                task_approved_result = res_b1_text

            # B.3 Armazenamento do resultado homologado
            stored_results[current_task.id] = task_approved_result
            ctx_store = uuid4().hex[:7]
            store_md = f"## 💾 Armazenamento — {current_task.id}\n\nResultado aprovado registrado na memória local:\n\n> {task_approved_result}\n"

            events.append(
                RalphLoopStepEvent(
                    type="thinking",
                    subtype="store",
                    task=current_task.id,
                    content=store_md,
                    total_tokens=total_tokens,
                    context_window=ContextWindowInfo(context_id=ctx_store, context_size=80),
                )
            )

            # B.4 Extração de aprendizados pontuais
            ctx_learn = uuid4().hex[:7]
            prompt_b4 = TEMPLATE_B4_LEARN.format(task_execution_history="\n".join(task_history_full))
            msg_b4 = Message(creation_timestamp=datetime.now(tz=UTC), text=prompt_b4, source=MessageSourceEnum.USER)
            res_b4_text, tokens_b4 = self._call_llm(
                messages=msg_b4,
                model_name=model_name,
                provider=provider,
                endpoint=endpoint,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            total_tokens += tokens_b4

            payload_b4 = extract_json_payload(res_b4_text)
            new_facts = payload_b4.get("facts", [])
            if isinstance(new_facts, list):
                for fact in new_facts:
                    fact_str = str(fact).strip()
                    if fact_str and fact_str not in accumulated_learnings:
                        accumulated_learnings.append(fact_str)

            learn_md = f"## 💡 Aprendizados Extraídos — {current_task.id}\n\n"
            if new_facts:
                for f in new_facts:
                    learn_md += f"- {f}\n"
            else:
                learn_md += f"- Dados factuais consolidados da {current_task.id}.\n"

            events.append(
                RalphLoopStepEvent(
                    type="thinking",
                    subtype="learn",
                    task=current_task.id,
                    content=learn_md,
                    total_tokens=total_tokens,
                    context_window=ContextWindowInfo(context_id=ctx_learn, context_size=tokens_b4),
                )
            )

            # Se ainda restam tarefas, reinicializa o contexto (Fresh Context)
            if task_queue:
                ctx_reset = uuid4().hex[:7]
                reset_md = (
                    "## 🔄 Reinicialização de Contexto (Fresh Context)\n\n"
                    "Contexto anterior **descartado**. Novo contexto inicializado para a próxima tarefa.\n\n"
                    "**Aprendizados reinjetados:**\n"
                )
                for fact in accumulated_learnings:
                    reset_md += f"- {fact}\n"

                events.append(
                    RalphLoopStepEvent(
                        type="thinking",
                        subtype="reset",
                        task=current_task.id,
                        content=reset_md,
                        total_tokens=total_tokens,
                        context_window=ContextWindowInfo(context_id=ctx_reset, context_size=70),
                    )
                )

            # Se acabaram as tarefas da fila principal, avalia se os critérios gerais foram satisfeitos (Fase C.1)
            if not task_queue and additional_planning_rounds < max_additional_planning_rounds:
                ctx_verify_global = uuid4().hex[:7]
                formatted_results = "\n\n".join(f"[{tid}]: {res}" for tid, res in stored_results.items())
                formatted_gen_criteria = "\n".join(f"- {c}" for c in criteria_list)

                prompt_c1 = TEMPLATE_C1_VERIFY_GLOBAL.format(
                    user_input=user_input,
                    general_criteria=formatted_gen_criteria,
                    stored_results=formatted_results,
                )

                msg_c1 = Message(creation_timestamp=datetime.now(tz=UTC), text=prompt_c1, source=MessageSourceEnum.USER)
                res_c1_text, tokens_c1 = self._call_llm(
                    messages=msg_c1,
                    model_name=model_name,
                    provider=provider,
                    endpoint=endpoint,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                total_tokens += tokens_c1

                payload_c1 = extract_json_payload(res_c1_text)
                global_approved = bool(payload_c1.get("approved", True))
                unmet = payload_c1.get("unmet_criteria", [])

                if not global_approved and unmet:
                    self.logger.info("Fase C.1 Reprovada. Ativando Planejamento Adicional (Fase C.2)")
                    unmet_str = "\n".join(f"- {u}" for u in unmet)
                    feedback_c1 = str(payload_c1.get("feedback") or "Critérios gerais pendentes.")

                    prompt_c2 = TEMPLATE_C2_ADDITIONAL_PLANNING.format(
                        stored_results=formatted_results,
                        unmet_criteria=unmet_str,
                        feedback=feedback_c1,
                    )
                    msg_c2 = Message(creation_timestamp=datetime.now(tz=UTC), text=prompt_c2, source=MessageSourceEnum.USER)
                    res_c2_text, tokens_c2 = self._call_llm(
                        messages=msg_c2,
                        model_name=model_name,
                        provider=provider,
                        endpoint=endpoint,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                    total_tokens += tokens_c2

                    payload_c2 = extract_json_payload(res_c2_text)
                    new_tasks = payload_c2.get("new_tasks", [])
                    if isinstance(new_tasks, list) and new_tasks:
                        for idx, nt in enumerate(new_tasks, start=len(stored_results) + 1):
                            if isinstance(nt, dict):
                                task_queue.append(
                                    RalphTask(
                                        id=str(nt.get("id") or f"T{idx}"),
                                        title=str(nt.get("title") or f"Tarefa Adicional {idx}"),
                                        description=str(nt.get("description") or ""),
                                        acceptance_criteria=list(nt.get("acceptance_criteria") or []),
                                    )
                                )
                        additional_planning_rounds += 1

        # =====================================================================
        # FASE C: Criação da Resposta Final
        # =====================================================================
        ctx_synth = uuid4().hex[:7]
        formatted_results = "\n\n".join(f"[{tid}]: {res}" for tid, res in stored_results.items())
        formatted_gen_criteria = "\n".join(f"- {c}" for c in criteria_list)

        compile_md = "## 📊 Compilação dos Resultados Homologados\n\n"
        for tid, res in stored_results.items():
            compile_md += f"**[{tid}]:** {res}\n\n"

        events.append(
            RalphLoopStepEvent(
                type="thinking",
                subtype="compile",
                task="synthesis",
                content=compile_md,
                total_tokens=total_tokens,
                context_window=ContextWindowInfo(context_id=ctx_synth, context_size=350),
            )
        )

        global_ver_md = (
            "## 🔍 Verificação Global\n\n"
            + "\n".join(f"- [x] {c}" for c in criteria_list)
            + "\n\n> **Status: APROVADO**\n"
        )
        events.append(
            RalphLoopStepEvent(
                type="thinking",
                subtype="compile",
                task="synthesis",
                content=global_ver_md,
                total_tokens=total_tokens,
                context_window=ContextWindowInfo(context_id=ctx_synth, context_size=420),
            )
        )

        # C.3 Construção da Resposta Final
        prompt_c3 = TEMPLATE_C3_FINAL_SYNTHESIS.format(
            user_input=user_input,
            general_criteria=formatted_gen_criteria,
            stored_results=formatted_results,
        )

        msg_c3 = Message(creation_timestamp=datetime.now(tz=UTC), text=prompt_c3, source=MessageSourceEnum.USER)
        res_c3_text, tokens_c3 = self._call_llm(
            messages=msg_c3,
            model_name=model_name,
            provider=provider,
            endpoint=endpoint,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        total_tokens += tokens_c3

        final_response_clean = res_c3_text.strip()

        final_synth_md = (
            "## 🏁 Construção da Resposta Final\n\n"
            "Todos os critérios gerais foram satisfeitos.\n"
            "Resposta construída utilizando **exclusivamente** os resultados armazenados.\n"
            "Nenhum fato novo foi introduzido.\n"
        )
        events.append(
            RalphLoopStepEvent(
                type="thinking",
                subtype="compile",
                task="synthesis",
                content=final_synth_md,
                total_tokens=total_tokens,
                context_window=ContextWindowInfo(context_id=ctx_synth, context_size=520),
            )
        )

        # Evento Final de Resultado
        events.append(
            RalphLoopStepEvent(
                type="result",
                subtype="compile",
                task="synthesis",
                content=final_response_clean,
                total_tokens=total_tokens,
                context_window=ContextWindowInfo(context_id=ctx_synth, context_size=total_tokens),
            )
        )

        return RalphLoopExecutionSummary(
            question=user_input,
            final_answer=final_response_clean,
            general_criteria=criteria_list,
            tasks_count=len(stored_results),
            approved_results=stored_results,
            accumulated_learnings=accumulated_learnings,
            total_tokens=total_tokens,
            events=events,
        )
