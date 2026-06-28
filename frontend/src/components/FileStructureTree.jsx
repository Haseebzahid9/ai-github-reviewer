const FILE_ITEMS = [
  { key: 'readme',           label: 'README'             },
  { key: 'license',          label: 'LICENSE'            },
  { key: 'gitignore',        label: '.gitignore'         },
  { key: 'env_example',      label: '.env.example'       },
  { key: 'dockerfile',       label: 'Dockerfile'         },
  { key: 'docker_compose',   label: 'docker-compose.yml' },
  { key: 'github_actions',   label: 'GitHub Actions'     },
  { key: 'tests_dir',        label: 'Tests directory'    },
  { key: 'src_dir',          label: 'src/ directory'     },
  { key: 'docs_dir',         label: 'docs/ directory'    },
  { key: 'requirements_txt', label: 'requirements.txt'   },
  { key: 'package_json',     label: 'package.json'       },
  { key: 'setup_py',         label: 'setup.py'           },
  { key: 'pyproject_toml',   label: 'pyproject.toml'     },
  { key: 'ci_files',         label: 'CI config files'    },
]

const CHECK_ICON = (
  <svg className="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"
       style={{ color: 'var(--success)' }}>
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
  </svg>
)
const CROSS_ICON = (
  <svg className="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"
       style={{ color: 'var(--danger)' }}>
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
  </svg>
)

export default function FileStructureTree({ filePresence }) {
  if (!filePresence) return null

  const present = FILE_ITEMS.filter((f) =>  filePresence[f.key])
  const missing  = FILE_ITEMS.filter((f) => !filePresence[f.key])

  return (
    <div className="card p-6 space-y-4 animate-slide-up">
      <p className="section-title">File Structure</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <p className="text-xs font-semibold mb-2" style={{ color: 'var(--success)' }}>
            Found ({present.length})
          </p>
          <ul className="space-y-1.5">
            {present.map((f) => (
              <li key={f.key} className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--muted)' }}>
                {CHECK_ICON}
                {f.label}
              </li>
            ))}
            {present.length === 0 && (
              <li className="text-xs italic" style={{ color: 'var(--muted)', opacity: 0.5 }}>None detected</li>
            )}
          </ul>
        </div>

        <div>
          <p className="text-xs font-semibold mb-2" style={{ color: 'var(--danger)' }}>
            Missing ({missing.length})
          </p>
          <ul className="space-y-1.5">
            {missing.map((f) => (
              <li key={f.key} className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--muted)', opacity: 0.6 }}>
                {CROSS_ICON}
                {f.label}
              </li>
            ))}
            {missing.length === 0 && (
              <li className="text-xs font-medium" style={{ color: 'var(--success)' }}>All files present!</li>
            )}
          </ul>
        </div>
      </div>
    </div>
  )
}
