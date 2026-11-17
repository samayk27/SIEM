import { useState } from 'react'
import {
  LuBan,
  LuDownload,
  LuKeyRound,
  LuLockKeyhole,
  LuMonitorSmartphone,
  LuRefreshCw,
  LuShieldAlert,
  LuUserCog,
  LuUserX,
  LuZap,
} from 'react-icons/lu'
import { useLabAction, useLabOverview } from '@/api/hooks'
import type { LabAction, LabActionRequest } from '@/api/types'
import styles from './lab.module.scss'

const ACTIONS: Array<{
  action: LabAction
  label: string
  description: string
  icon: typeof LuZap
  tone?: string
}> = [
  {
    action: 'login_failure',
    label: 'Failed login',
    description: 'Generate one failed sign-in from the selected IP.',
    icon: LuLockKeyhole,
  },
  {
    action: 'file_download',
    label: 'Download sensitive file',
    description: 'Access a confidential enterprise resource.',
    icon: LuDownload,
  },
  {
    action: 'api_request',
    label: 'API request',
    description: 'Exercise the per-user API rate limit.',
    icon: LuZap,
  },
  {
    action: 'privilege_change',
    label: 'Change user privilege',
    description: 'Record a privileged role change.',
    icon: LuUserCog,
    tone: 'warning',
  },
  {
    action: 'restricted_access',
    label: 'Attempt restricted access',
    description: 'Trigger a preventive access denial.',
    icon: LuShieldAlert,
    tone: 'warning',
  },
  {
    action: 'device_register',
    label: 'Register device',
    description: 'Add a new device to the enterprise workspace.',
    icon: LuMonitorSmartphone,
  },
]

export function Component(): React.ReactElement {
  const { data, isLoading } = useLabOverview()
  const action = useLabAction()
  const [username, setUsername] = useState('alex.chen')
  const [sourceIp, setSourceIp] = useState('10.10.20.15')
  const [resource, setResource] = useState('finance-q4.xlsx')

  const execute = (labAction: LabAction): void => {
    const payload: LabActionRequest = {
      action: labAction,
      username,
      source_ip: sourceIp,
      resource,
      target_username: username,
    }
    action.mutate(payload)
  }

  if (isLoading || !data) {
    return <div className={styles.loading}>Loading enterprise lab...</div>
  }

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <div>
          <div className={styles.eyebrow}>ISOLATED DEMO TENANT</div>
          <h2 className={styles.title}>{data.tenant.name}</h2>
          <p className={styles.subtitle}>
            Perform realistic enterprise operations. Every action generates
            telemetry for the SOC and is subject to the controls below.
          </p>
        </div>
        <div className={styles.protected}>
          <span className={styles.statusDot} />
          Protected
        </div>
      </section>

      <section className={styles.controls}>
        <label>
          Acting user
          <select value={username} onChange={(e) => setUsername(e.target.value)}>
            {data.users.map((user) => (
              <option key={String(user.username)} value={String(user.username)}>
                {String(user.username)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Source IP
          <input value={sourceIp} onChange={(e) => setSourceIp(e.target.value)} />
        </label>
        <label>
          Resource
          <select value={resource} onChange={(e) => setResource(e.target.value)}>
            {data.resources.map((item) => (
              <option key={String(item.name)} value={String(item.name)}>
                {String(item.name)} · {String(item.classification)}
              </option>
            ))}
          </select>
        </label>
      </section>

      <div className={styles.grid}>
        <section className={styles.actionPanel}>
          <div className={styles.sectionHeader}>
            <div>
              <h3>Enterprise operations</h3>
              <p>These are real actions inside the isolated workspace.</p>
            </div>
            <LuRefreshCw className={action.isPending ? styles.spinning : ''} />
          </div>
          <div className={styles.actionGrid}>
            {ACTIONS.map((item) => (
              <button
                type="button"
                key={item.action}
                className={`${styles.actionCard} ${
                  item.tone === 'warning' ? styles.warning : ''
                }`}
                disabled={action.isPending}
                onClick={() => execute(item.action)}
              >
                <item.icon className={styles.actionIcon} />
                <strong>{item.label}</strong>
                <span>{item.description}</span>
              </button>
            ))}
          </div>
        </section>

        <section className={styles.policyPanel}>
          <div className={styles.sectionHeader}>
            <div>
              <h3>Active controls</h3>
              <p>Prevention policies applied before telemetry is emitted.</p>
            </div>
            <LuShieldAlert />
          </div>
          <Policy
            label="API requests / minute"
            value={String(data.policies.api_requests_per_minute)}
          />
          <Policy
            label="Downloads / window"
            value={String(data.policies.downloads_per_window)}
          />
          <Policy
            label="Download window"
            value={`${String(data.policies.download_window_seconds)} seconds`}
          />
          <div className={styles.controlList}>
            <button type="button" onClick={() => execute('disable_user')}>
              <LuUserX /> Disable selected user
            </button>
            <button type="button" onClick={() => execute('block_ip')}>
              <LuBan /> Block selected IP
            </button>
            <button type="button" onClick={() => execute('revoke_session')}>
              <LuKeyRound /> Revoke user sessions
            </button>
          </div>
        </section>
      </div>

      <section className={styles.eventsPanel}>
        <div className={styles.sectionHeader}>
          <div>
            <h3>Workspace telemetry</h3>
            <p>Recent events emitted to the SIEM pipeline.</p>
          </div>
          <span className={styles.liveBadge}>LIVE</span>
        </div>
        <div className={styles.eventList}>
          {data.recent_events.length === 0 ? (
            <div className={styles.empty}>
              Run an operation to create telemetry.
            </div>
          ) : (
            data.recent_events.map((event) => (
              <div className={styles.eventRow} key={event.id}>
                <span className={styles.eventSeverity}>{event.severity}</span>
                <strong>{event.event_type ?? 'event'}</strong>
                <span>{event.username ?? 'system'}</span>
                <span>{event.source_ip ?? 'internal'}</span>
                <time>{new Date(event.timestamp).toLocaleTimeString()}</time>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  )
}

Component.displayName = 'Enterprise Lab'

function Policy({
  label,
  value,
}: {
  label: string
  value: string
}): React.ReactElement {
  return (
    <div className={styles.policy}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}
