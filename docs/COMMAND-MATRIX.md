# Command and source matrix

Commands below are procedures for the specified actor, not permission for a detached worker to run owner-only operations. Native help is checked in an isolated test home. Generic public acquisition, guarded identity rendering and clean-user onboarding remain pending; factory acceptance is explicitly not a public install command.

| Command / operation | Actor | Owning source | Evidence / limitation |
| --- | --- | --- | --- |
| `python3 -B -m pytest -q -p no:cacheprovider` | scoped maker/verifier | tests/release | Real source regression, not full release acceptance |
| `python3 -B scripts/validate_customization.py /absolute/private/customization.json` | owner/operator | scripts/validate_customization.py and docs/templates/customization.schema.json | Two fictional forms, invalid fields, no installation/identity output |
| `python3 -B scripts/create_brain_os.py /absolute/private/new-vault` | owner/new-vault operator | scripts/create_brain_os.py | Linux no-replace; parent must exist; tests cover race/symlink/interruption/links |
| `hermes profile install /absolute/extracted/profiles/forge --name forge` | owner/disposable test operator | accepted native hermes_cli/profile_distribution.py | Six native installs exercised; no force/activation/aliases |
| `hermes profile update forge` | owner/operator | native update_distribution | Same-version preservation only; distribution-owned personalized Soul is unsafe without a reviewed plan |
| `hermes profile export --help`, `hermes profile import --help` | owner/operator | native profiles export_profile/import_profile | Native APIs exercised on all six; backup is private, credential recovery separate |
| `hermes model`, `hermes setup` | owner only | native CLI/provider docs | Real credentials/inference not exercised by maker |
| `kanban_show`, `kanban_comment`, `kanban_heartbeat` | admitted worker/controller | native Kanban tools | Durable state/readback, not shell board mutation |
| `kanban_create`, `kanban_link`, authentic admit/release/seal tools | controller only | compatible governed native runtime | Exact blocked/link/timing/release and reviewer sequence required; maker cannot launch next role |
| Installed timing adapter and native stateless Git evidence | scoped controller/maker | reviewed compatible extension sources | Public rights/acquisition unresolved; no invented public install path |

Sources: [Bible reference](bible/25-reference.md), [capability status](CAPABILITY-STATUS.md), [official CLI documentation](https://hermes-agent.nousresearch.com/docs/reference/cli-commands), [native command checks](../tests/release/test_generic_commands.py).

All retained command results are real test outputs. Help/source verification supplements executable onboarding trials. An expected example must never be presented as a measured receipt.
