# External References

Use these links when designing features. Only fetch URLs when the keywords match your design topic.

## GitHub Issues and Discussions

| Keywords | Link | Description |
|----------|------|-------------|
| substance, materials, linux, crash, baking | [Issue #297](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/issues/297) | Adobe Substance Materials crash on Amazon Linux 2023 at "Baking Substance Materials" step. Works on RHEL 9/10. |
| redshift, freeze, linux, timeout, progress | [Issue #296](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/issues/296) | Redshift sporadic freezing on Linux. Workaround: set timeouts via submitter. |
| arnold, c4dtoa, linux, 2026, crash, gpu driver | [Issue #386](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/issues/386) | C4DtoA crashes on Linux 2026. Requires c4dtoa 4.8.6.2+ with GPU driver 580.127+. |

## Documentation

| Keywords | Link | Description |
|----------|------|-------------|
| openjd, session, job template, step, task, environment, action | [OpenJD Sessions](https://github.com/OpenJobDescription/openjd-sessions-for-python) | OpenJD Sessions for Python — runtime library for executing Open Job Description jobs |
| adaptor, runtime, lifecycle, daemon, run | [OpenJD Adaptor Runtime](https://github.com/OpenJobDescription/openjd-adaptor-runtime-for-python) | OpenJD Adaptor Runtime — base framework for the cinema4d-openjd CLI |
| conda, recipes, packaging, smf | [Deadline Cloud Samples](https://github.com/aws-deadline/deadline-cloud-samples) | Public conda recipes and samples for Cinema 4D, Arnold, V-Ray, INSYDIUM |
| user guide, setup, submitter, installation | [User Guide](https://docs.aws.amazon.com/deadline-cloud/latest/userguide/maxon-cinema-4d.html) | Official Cinema 4D for Deadline Cloud user guide |
| software architecture, adaptor, submitter, client | [Software Architecture](../../../docs/software_arch.md) | Architecture overview of submitter and adaptor components |

## Plugin Documentation

| Plugin | Keywords | Link | Description |
|--------|----------|------|-------------|
| Redshift | redshift, gpu, render, aov | [Redshift for C4D](https://help.maxon.net/r3d/cinema/en-us/) | Redshift render settings, AOVs, materials. Bundled with C4D 2024+. |
| Arnold | arnold, c4dtoa, shader, aov | [Arnold for C4D](https://help.autodesk.com/view/ARNOL/ENU/?guid=arnold_for_cinema_4d) | Arnold render settings, shaders, installation |
| V-Ray | vray, chaos, render elements | [V-Ray for C4D](https://docs.chaos.com/display/VC4D/) | V-Ray render settings, materials, render elements |
| INSYDIUM | xparticles, insydium, particles | [INSYDIUM](https://insydium.ltd/help/) | X-Particles and INSYDIUM Fused documentation |
| Cargo | cargo, kitbash, assets | [Cargo](https://kit-bash.myshopify.com/pages/cargo) | No special fleet config needed. Use File > Save Project with Assets. |

## Conda Recipes (External)

| Recipe | Link | Description |
|--------|------|-------------|
| Cinema 4D 2024 | [cinema4d-2024](https://github.com/aws-deadline/deadline-cloud-samples/tree/mainline/conda_recipes/cinema4d-2024) | Cinema 4D 2024 conda recipe |
| Cinema 4D 2025 | [cinema4d-2025](https://github.com/aws-deadline/deadline-cloud-samples/tree/mainline/conda_recipes/cinema4d-2025) | Cinema 4D 2025 conda recipe |
| Cinema 4D OpenJD | [cinema4d-openjd](https://github.com/aws-deadline/deadline-cloud-samples/tree/mainline/conda_recipes/cinema4d-openjd) | Adaptor conda recipe (Windows and Linux) |
| Arnold (C4DtoA) | [cinema4d-c4dtoa-2025](https://github.com/aws-deadline/deadline-cloud-samples/tree/mainline/conda_recipes/cinema4d-c4dtoa-2025) | Arnold plugin conda recipe |
| V-Ray | [cinema4d-vray-2025](https://github.com/aws-deadline/deadline-cloud-samples/tree/mainline/conda_recipes/cinema4d-vray-2025) | V-Ray plugin conda recipe |
| INSYDIUM | [cinema4d-insydium-2025](https://github.com/aws-deadline/deadline-cloud-samples/tree/mainline/conda_recipes/cinema4d-insydium-2025) | X-Particles conda recipe |
| Red Giant | [Host Config Script](https://github.com/aws-deadline/deadline-cloud-samples/tree/mainline/host_configuration_scripts/cinema4d/cinema4d_redgiant) | Red Giant host configuration (not conda) |

## Cinema 4D SDK

| Keywords | Link | Description |
|----------|------|-------------|
| python, sdk, api, c4d module | [Python SDK](https://developers.maxon.net/docs/py/2026/) | Cinema 4D Python SDK documentation |
| c++, sdk, plugin | [C++ SDK](https://developers.maxon.net/docs/cpp/2026/) | Cinema 4D C++ SDK documentation |
| forum, developer, support | [Developer Forum](https://developers.maxon.net/forum/) | Maxon developer forum |
