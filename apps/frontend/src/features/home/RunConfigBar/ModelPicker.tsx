import { Link } from 'react-router-dom'
import { Button } from '@/components/primitives/Button'
import { Skeleton } from '@/components/primitives/Skeleton'
import { modelLabel } from '@/domain/services/modelSort'
import { ModelTable } from '@/features/models/ModelTable'
import { ROUTES } from '@/router/routes'
import { useRunConfig } from '@/state/RunConfigContext'
import styles from './RunConfigBar.module.css'

/**
 * Escolha do modelo em uso: a lista do catálogo (`GET /v1/models`) com preço, contexto e vazão,
 * ordenável pelas colunas e com seleção única.
 */
export function ModelPicker(): JSX.Element {
  const { config, models, modelsStatus, reloadModels, setModelName } = useRunConfig()
  const selected = models.find((model) => model.model_name === config.modelName)

  return (
    <section className={styles.modelSection} aria-label="Modelo">
      <div className={styles.modelHeader}>
        <span className={styles.modelHeading}>
          Modelo <strong className={styles.modelCurrent}>{selected ? modelLabel(selected) : config.modelName}</strong>
        </span>
        <Link to={ROUTES.models} className={styles.manageLink}>
          Gerenciar modelos
        </Link>
      </div>

      {modelsStatus === 'loading' ? <Skeleton height="120px" radius="var(--radius-lg)" /> : null}

      {modelsStatus === 'error' ? (
        <div className={styles.modelNotice} role="alert">
          Não foi possível carregar o catálogo de modelos. O modelo em uso continua valendo.
          <Button variant="secondary" size="sm" onClick={reloadModels}>
            Tentar de novo
          </Button>
        </div>
      ) : null}

      {modelsStatus === 'ready' && models.length === 0 ? (
        <div className={styles.modelNotice}>
          Nenhum modelo cadastrado. <Link to={ROUTES.models}>Cadastre o primeiro.</Link>
        </div>
      ) : null}

      {modelsStatus === 'ready' && models.length > 0 ? (
        <ModelTable
          models={models}
          label="Modelos disponíveis"
          selectedModel={config.modelName}
          onSelect={setModelName}
        />
      ) : null}
    </section>
  )
}
