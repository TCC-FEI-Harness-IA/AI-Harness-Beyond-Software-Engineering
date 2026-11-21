import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes, useLocation } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { HttpError } from '@/api/errors/HttpError'
import { TopBar } from '@/components/layout/TopBar'
import { ROUTES } from '@/router/routes'
import { authApiFor, CREDENCIAL_VALIDA, fakeAuthApi, renderWithAuth, SESSAO_ANA } from '@/test/renderWithAuth'
import { CredentialPage } from './CredentialPage'
import { LoginPage } from './LoginPage'
import { RegisterPage } from './RegisterPage'
import { RequireAuth } from './RequireAuth'
import { SessionExpiredBanner } from './SessionExpiredBanner'

const CHAVE = 'sk-or-v1-chave-de-teste'

function Local(): JSX.Element {
  const location = useLocation()
  return <p>local:{location.pathname}</p>
}

function rotas(): JSX.Element {
  return (
    <Routes>
      <Route path={ROUTES.login} element={<LoginPage />} />
      <Route path={ROUTES.register} element={<RegisterPage />} />
      <Route path={ROUTES.credential} element={<CredentialPage />} />
      <Route path="*" element={<Local />} />
    </Routes>
  )
}

async function preencherLogin(chave = ''): Promise<void> {
  const user = userEvent.setup()
  await user.type(await screen.findByLabelText('E-mail'), 'ana@exemplo.com')
  await user.type(screen.getByLabelText('Senha'), 'senha muito boa 1')
  if (chave) await user.type(screen.getByLabelText(/Chave OpenRouter/), chave)
  await user.click(screen.getByRole('button', { name: 'Entrar' }))
}

describe('Login', () => {
  it('entra sem chave e volta para a página pedida', async () => {
    const api = fakeAuthApi()
    renderWithAuth(rotas(), { api, route: '/entrar?next=/historico' })

    await preencherLogin()

    await screen.findByText('local:/historico')
    expect(api.login).toHaveBeenCalledWith('ana@exemplo.com', 'senha muito boa 1')
    expect(api.saveCredential).not.toHaveBeenCalled()
  })

  it('envia a chave inicial uma vez e não a guarda no navegador', async () => {
    const api = fakeAuthApi()
    renderWithAuth(rotas(), { api, route: '/entrar' })

    await preencherLogin(CHAVE)

    await screen.findByText('local:/')
    expect(api.saveCredential).toHaveBeenCalledWith(CHAVE)
    const armazenado = JSON.stringify({ ...window.localStorage }) + JSON.stringify({ ...window.sessionStorage })
    expect(armazenado).not.toContain('sk-or')
  })

  it('chave recusada após o login leva à correção da chave', async () => {
    const api = fakeAuthApi({
      saveCredential: vi.fn().mockRejectedValue(new HttpError(422, 'A OpenRouter recusou a chave informada.')),
      getCredentialStatus: vi.fn().mockResolvedValue({ status: 'invalid', available: false, expiresAt: null }),
    })
    renderWithAuth(rotas(), { api, route: '/entrar' })

    await preencherLogin(CHAVE)

    expect(await screen.findByRole('heading', { name: 'Chave OpenRouter' })).toBeInTheDocument()
    expect(await screen.findByText(/recusou/)).toBeInTheDocument()
  })

  it('credenciais inválidas mostram o erro e limpam senha e chave', async () => {
    const api = fakeAuthApi({ login: vi.fn().mockRejectedValue(new HttpError(401, 'E-mail ou senha inválidos.')) })
    renderWithAuth(rotas(), { api, route: '/entrar' })

    await preencherLogin(CHAVE)

    expect(await screen.findByRole('alert')).toHaveTextContent('E-mail ou senha inválidos.')
    expect(screen.getByLabelText('Senha')).toHaveValue('')
    expect(screen.getByLabelText(/Chave OpenRouter/)).toHaveValue('')
    expect(api.saveCredential).not.toHaveBeenCalled()
  })

  it('usuário já autenticado vê a conta atual em vez do formulário', async () => {
    renderWithAuth(rotas(), { api: authApiFor('user'), route: '/entrar' })

    expect(await screen.findByText(/ana@exemplo.com/)).toBeInTheDocument()
    expect(screen.queryByLabelText('Senha')).not.toBeInTheDocument()
  })
})

describe('Cadastro', () => {
  it('confere a confirmação da senha antes de enviar', async () => {
    const api = fakeAuthApi()
    renderWithAuth(rotas(), { api, route: '/cadastro' })
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('E-mail'), 'ana@exemplo.com')
    await user.type(screen.getByLabelText('Senha'), 'senha muito boa 1')
    await user.type(screen.getByLabelText('Confirme a senha'), 'outra senha 123')
    await user.click(screen.getByRole('button', { name: 'Criar conta' }))

    expect(screen.getByRole('alert')).toHaveTextContent(/não conferem/)
    expect(api.register).not.toHaveBeenCalled()
  })

  it('cria a conta, entra e configura a chave', async () => {
    const api = fakeAuthApi()
    renderWithAuth(rotas(), { api, route: '/cadastro' })
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('E-mail'), 'ana@exemplo.com')
    await user.type(screen.getByLabelText('Senha'), 'senha muito boa 1')
    await user.type(screen.getByLabelText('Confirme a senha'), 'senha muito boa 1')
    await user.type(screen.getByLabelText(/Chave OpenRouter/), CHAVE)
    await user.click(screen.getByRole('button', { name: 'Criar conta' }))

    await screen.findByText('local:/')
    expect(api.register).toHaveBeenCalledWith('ana@exemplo.com', 'senha muito boa 1')
    expect(api.saveCredential).toHaveBeenCalledWith(CHAVE)
  })

  it('mostra a recusa do servidor', async () => {
    const api = fakeAuthApi({ register: vi.fn().mockRejectedValue(new HttpError(409, 'Não foi possível concluir o cadastro com este e-mail.')) })
    renderWithAuth(rotas(), { api, route: '/cadastro' })
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('E-mail'), 'ana@exemplo.com')
    await user.type(screen.getByLabelText('Senha'), 'senha muito boa 1')
    await user.type(screen.getByLabelText('Confirme a senha'), 'senha muito boa 1')
    await user.click(screen.getByRole('button', { name: 'Criar conta' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/cadastro/)
  })
})

describe('Chave OpenRouter da sessão', () => {
  it('substitui a chave e limpa o campo depois do envio', async () => {
    const api = authApiFor('user')
    renderWithAuth(rotas(), { api, route: '/conta/chave' })
    const user = userEvent.setup()
    expect(await screen.findByText(/Nenhuma chave configurada/)).toBeInTheDocument()

    await user.type(screen.getByLabelText(/Nova chave OpenRouter/), CHAVE)
    await user.click(screen.getByRole('button', { name: 'Salvar chave' }))

    expect(await screen.findByText(/Chave válida/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Nova chave OpenRouter/)).toHaveValue('')
    expect(screen.queryByDisplayValue(CHAVE)).not.toBeInTheDocument()
  })

  it('remove a chave da sessão', async () => {
    const api = fakeAuthApi({
      getCurrentSession: vi.fn().mockResolvedValue(SESSAO_ANA),
      getCredentialStatus: vi.fn().mockResolvedValue(CREDENCIAL_VALIDA),
    })
    renderWithAuth(rotas(), { api, route: '/conta/chave' })
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Remover chave' }))

    expect(api.deleteCredential).toHaveBeenCalled()
    expect(await screen.findByText(/Nenhuma chave configurada/)).toBeInTheDocument()
  })

  it('visitante é convidado a entrar', async () => {
    renderWithAuth(rotas(), { route: '/conta/chave' })

    expect(await screen.findByRole('link', { name: 'Entrar' })).toHaveAttribute('href', '/entrar?next=%2Fconta%2Fchave')
  })
})

describe('Proteção das páginas privadas', () => {
  it('visitante vê o convite para entrar e nenhum conteúdo privado', async () => {
    renderWithAuth(<RequireAuth><p>conteúdo privado</p></RequireAuth>, { route: '/historico' })

    expect(await screen.findByRole('link', { name: 'Entrar' })).toHaveAttribute('href', '/entrar?next=%2Fhistorico')
    expect(screen.getByRole('link', { name: /resultados oficiais/i })).toBeInTheDocument()
    expect(screen.queryByText('conteúdo privado')).not.toBeInTheDocument()
  })

  it('usuário autenticado vê o conteúdo', async () => {
    renderWithAuth(<RequireAuth><p>conteúdo privado</p></RequireAuth>, { api: authApiFor('user') })

    expect(await screen.findByText('conteúdo privado')).toBeInTheDocument()
  })

  it('sem chave válida, uma página de execução pede a configuração da chave', async () => {
    renderWithAuth(<RequireAuth requireCredential><p>executar</p></RequireAuth>, { api: authApiFor('user') })

    expect(await screen.findByRole('link', { name: /Configurar chave/ })).toHaveAttribute('href', '/conta/chave')
    expect(screen.queryByText('executar')).not.toBeInTheDocument()
  })

  it('com chave válida, a página de execução aparece', async () => {
    renderWithAuth(<RequireAuth requireCredential><p>executar</p></RequireAuth>, { api: authApiFor('user-with-key') })

    expect(await screen.findByText('executar')).toBeInTheDocument()
  })
})

describe('Barra superior e aviso de sessão expirada', () => {
  it('visitante vê só as páginas públicas e os atalhos de acesso', async () => {
    renderWithAuth(<TopBar />)

    expect(await screen.findByRole('link', { name: 'Entrar' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Criar conta' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'BenchMark' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Análise' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Histórico' })).not.toBeInTheDocument()
  })

  it('usuário vê a conta, o estado da chave e sai', async () => {
    const api = authApiFor('user')
    renderWithAuth(<TopBar />, { api })
    const user = userEvent.setup()

    expect(await screen.findByText('ana@exemplo.com')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Histórico' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Chave: ausente/ })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Sair' }))

    await waitFor(() => expect(api.logout).toHaveBeenCalled())
    expect(await screen.findByRole('link', { name: 'Entrar' })).toBeInTheDocument()
  })

  it('o aviso de sessão expirada oferece entrar de novo', async () => {
    const { emitUnauthorized } = await import('@/api/authEvents')
    const { act } = await import('@testing-library/react')
    renderWithAuth(<SessionExpiredBanner />, { api: authApiFor('user') })
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument())

    act(() => emitUnauthorized())

    expect(await screen.findByRole('alert')).toHaveTextContent(/sessão terminou/)
    expect(screen.getByRole('link', { name: 'Entrar novamente' })).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Fechar aviso' }))
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
