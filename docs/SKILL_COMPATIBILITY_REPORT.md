# Reporte de compatibilidad de skills

## Reglas

- **R1**: Licencia efectiva = frontmatter `license` normalizada o LICENSE del repo. Permitidas: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, CC0-1.0, CC-BY-4.0, CC-BY-SA-4.0, Unlicense. AGPL/GPL/LGPL (permiten redistribuir bajo condiciones copyleft; excluidas por politica del proyecto), NC/ND, propietaria, desconocida o repo sin LICENSE: `license-not-allowed:<valor>`.
- **R2**: Copias/ports/traducciones (`docs/<lang>/`, `.kiro/`, `.cursor/`, `.cursor-plugin/`, `.agents/`, `.codex/`, `pi/`, `examples/`, `tests/`, `fixtures/`) con otra copia canonica del mismo nombre: `non-canonical-copy`. Prioridad canonica: `skills/`|`agents/` raiz > `plugin(s)/.../skills` > otros.
- **R3**: Duplicados por nombre normalizado o hash identico de SKILL.md. Las propias siempre ganan (`duplicate-of-own:<n>`); entre externas: scientific-agent-skills > Anthropic-Cybersecurity-Skills > diagram-design > ECC > otras, luego ruta canonica y ruta mas corta (`duplicate-of:<id>`).
- **R4**: Skill con codigo (.bash .bat .bin .cjs .cmd .dll .exe .go .js .mjs .ps1 .py .rb .sh .so .ts) referenciado en su SKILL.md (nombre de archivo o `scripts/`): `requires-script-review`. Si no, se aprueba como solo instrucciones: `files` solo incluye .md/.txt/.json/.yaml/.yml/.csv/.toml y el codigo queda en `excluded_code`.
- **R5**: agentmemory: `requires-service:agentmemory`; rea: `requires-toolchain:rea`; OpenViking queda separado por politica del proyecto (R1, AGPL-3.0); awesome-harness-engineering solo referencia (sin licencia).
- **R6**: Solo seguridad defensiva: terminos ofensivos fuertes (exploit development, red team, c2, credential dumping, lateral movement, privilege escalation, ddos, jailbreak, keylogger...) en nombre+descripcion; terminos debiles (payload, shellcode, ransomware, evasion) solo con verbo ofensivo previo (build, create, deploy...). Se exime si hay contexto defensivo (detect, hunt, investigate, analyze, respond, mitigate, defend, prevent, against... antes o detection/mitigation/analysis... despues). Resultado `offensive-security`.
- **R7**: Patrones inseguros en SKILL.md/agente: ignore-previous-instructions, curl-pipe-shell, iwr-pipe-iex, rm-rf-root, dangerously-skip-permissions, bypassPermissions, disable-hook-guard-sandbox, base64-blob (`rm -rf /` solo raiz). Resultado `unsafe-pattern:<id>`.
- **R8**: Calidad: nombre `^[a-z0-9][a-z0-9-]{0,63}$` (`invalid-name`), descripcion >= 20 caracteres, SKILL.md <= 100 KB.
- **R9**: Dominios por palabras clave sobre nombre+descripcion+ruta: general, data-science, games, web, sre-devops, security-defensive, automation. Sin dominio: `out-of-scope-domain`. Tier `active`: los 2 mejores por dominio (puntaje de coincidencias, desempate SKILL.md menor, luego id), maximo 14; resto aprobado = `catalog`.
- **A**: Agentes: R1/R2/R3/R6/R7/R8/R9 mas modelo exactamente `sonnet` o `haiku` (`model-opus-not-allowed`, `model-missing-or-inherit`); claves `hooks`, `mcpServers`, `permissionMode` -> `agent-config-not-allowed:<k>`; tier siempre `catalog`.

## Matriz dominio x decision (skills)

| Dominio | approved | requires-review | rejected |
|---|---|---|---|
| general | 259 | 51 | 346 |
| data-science | 142 | 124 | 84 |
| games | 2 | 0 | 2 |
| web | 152 | 23 | 207 |
| sre-devops | 258 | 24 | 90 |
| security-defensive | 767 | 76 | 165 |
| automation | 105 | 34 | 101 |
| (sin dominio) | 0 | 0 | 424 |

## Duplicados

- Skills: 280 grupos por nombre, 144 por hash.
- Agentes: 63 grupos por nombre, 0 por hash.

Colisiones con nombres propios (prioridad propia):

- `ECC--api-design` (.agents/skills/api-design)
- `ECC--api-design` (.kiro/skills/api-design)
- `ECC--api-design` (docs/es/skills/api-design)
- `ECC--api-design` (docs/ja-JP/skills/api-design)
- `ECC--api-design` (docs/tr/skills/api-design)
- `ECC--api-design` (docs/zh-CN/skills/api-design)
- `ECC--api-design` (pi/core/skills/api-design)
- `ECC--api-design` (skills/api-design)
- `ECC--code-reviewer` (.kiro/agents/code-reviewer.md)
- `ECC--code-reviewer` (agents/code-reviewer.md)
- `ECC--code-reviewer` (docs/es/agents/code-reviewer.md)
- `ECC--code-reviewer` (docs/ja-JP/agents/code-reviewer.md)
- `ECC--code-reviewer` (docs/ko-KR/agents/code-reviewer.md)
- `ECC--code-reviewer` (docs/pt-BR/agents/code-reviewer.md)
- `ECC--code-reviewer` (docs/tr/agents/code-reviewer.md)
- `ECC--code-reviewer` (docs/zh-CN/agents/code-reviewer.md)
- `ECC--code-reviewer` (docs/zh-TW/agents/code-reviewer.md)
- `ECC--market-research` (.agents/skills/market-research)
- `ECC--market-research` (.cursor/skills/market-research)
- `ECC--market-research` (docs/ja-JP/skills/market-research)
- `ECC--market-research` (docs/zh-CN/skills/market-research)
- `ECC--market-research` (skills/market-research)
- `ECC--security-reviewer` (.kiro/agents/security-reviewer.md)
- `ECC--security-reviewer` (agents/security-reviewer.md)
- `ECC--security-reviewer` (docs/es/agents/security-reviewer.md)
- `ECC--security-reviewer` (docs/ja-JP/agents/security-reviewer.md)
- `ECC--security-reviewer` (docs/ko-KR/agents/security-reviewer.md)
- `ECC--security-reviewer` (docs/pt-BR/agents/security-reviewer.md)
- `ECC--security-reviewer` (docs/tr/agents/security-reviewer.md)
- `ECC--security-reviewer` (docs/zh-CN/agents/security-reviewer.md)
- `ECC--security-reviewer` (docs/zh-TW/agents/security-reviewer.md)
- `diagram-design--diagram-design` (skills/diagram-design)

## requires-review por repo

- **Anthropic-Cybersecurity-Skills**: 55 (ej.: `Anthropic-Cybersecurity-Skills--achieving-cmmc-level-2-compliance`, `Anthropic-Cybersecurity-Skills--analyzing-browser-forensics-with-hindsight`, `Anthropic-Cybersecurity-Skills--analyzing-cloud-storage-access-patterns`, `Anthropic-Cybersecurity-Skills--analyzing-malicious-url-with-urlscan`, `Anthropic-Cybersecurity-Skills--analyzing-network-flow-data-with-netflow`, `Anthropic-Cybersecurity-Skills--analyzing-powershell-script-block-logging`, `Anthropic-Cybersecurity-Skills--analyzing-threat-landscape-with-misp`, `Anthropic-Cybersecurity-Skills--analyzing-web-server-logs-for-intrusion`, `Anthropic-Cybersecurity-Skills--building-vulnerability-exception-tracking-system`, `Anthropic-Cybersecurity-Skills--conducting-cyber-risk-assessment-with-nist-800-30`)
- **ECC**: 12 (ej.: `ECC--ck`, `ECC--council-multi-model`, `ECC--delivery-gate`, `ECC--docs-governance`, `ECC--ecc-contribution-review`, `ECC--frontend-design-direction`, `ECC--ios-icon-gen`, `ECC--ito-baskets`, `ECC--master-agreement-generator`, `ECC--terminal-opener`)
- **OpenViking**: 0
- **agentmemory**: 0
- **awesome-harness-engineering**: 0
- **diagram-design**: 0
- **rea**: 0
- **scientific-agent-skills**: 114 (ej.: `scientific-agent-skills--13c-metabolic-flux`, `scientific-agent-skills--alphagenome`, `scientific-agent-skills--analytical-method-validation`, `scientific-agent-skills--arbor`, `scientific-agent-skills--arboreto`, `scientific-agent-skills--autoskill`, `scientific-agent-skills--bulk-rnaseq`, `scientific-agent-skills--cantera`, `scientific-agent-skills--cellprofiler`, `scientific-agent-skills--citation-management`)

## Filtro de seguridad ofensiva (R6)

Rechazadas: 36; mantenidas con frase defensiva: 47.

Ejemplos rechazados:

- `Anthropic-Cybersecurity-Skills--abusing-dpapi-for-credential-access` ['red-team']: Extract and decrypt Windows DPAPI-protected secrets (Credential Manager, browser logins/cookies, Wi-Fi credentials, KeeP
- `Anthropic-Cybersecurity-Skills--abusing-shadow-credentials-for-privesc` ['red-team']: Take over Active Directory accounts by writing attacker-controlled public keys to msDS-KeyCredentialLink (Shadow Credent
- `Anthropic-Cybersecurity-Skills--auditing-entra-id-with-aadinternals` ['red-team']: Drive the AADInternals PowerShell toolkit to perform Microsoft Entra ID tenant reconnaissance, access-token acquisition 
- `Anthropic-Cybersecurity-Skills--building-c2-infrastructure-with-sliver-framework` ['c2', 'red-team']: Deploy and harden a Sliver C2 team server (BishopFox's Go-based adversary emulation framework) with multi-protocol liste
- `Anthropic-Cybersecurity-Skills--building-c2-redirector-infrastructure` ['c2', 'red-team']: Build dumb-pipe and traffic-filtering C2 redirectors with nginx (proxy_pass) and Apache (mod_rewrite), deriving filter r
- `Anthropic-Cybersecurity-Skills--building-red-team-c2-infrastructure-with-havoc` ['c2', 'red-team']: Deploy and configure the Havoc C2 framework (teamserver, HTTPS/HTTP/SMB
- `Anthropic-Cybersecurity-Skills--conducting-full-scope-red-team-engagement` ['red team', 'red-team']: Plan and execute a comprehensive, MITRE ATT&CK-aligned red team engagement spanning threat modeling, reconnaissance, ini
- `Anthropic-Cybersecurity-Skills--conducting-pass-the-ticket-attack` ['lateral movement']: Perform Pass-the-Ticket (PtT) lateral movement by extracting Kerberos TGT/TGS tickets from LSASS memory on a compromised
- `Anthropic-Cybersecurity-Skills--conducting-spearphishing-simulation-campaign` ['payloads']: Run a targeted spearphishing simulation for initial access by developing OSINT-derived pretexts, building payloads (HTML
- `Anthropic-Cybersecurity-Skills--continuous-llm-red-teaming-with-promptfoo` ['jailbreak', 'red-teaming']: Wires Promptfoo and DeepTeam into CI/CD for automated, repeatable red-teaming of LLM apps against OWASP LLM Top 10, OWAS

Ejemplos mantenidos (termino ofensivo en contexto defensivo):

- `Anthropic-Cybersecurity-Skills--analyzing-cobaltstrike-malleable-c2-profiles` ['c2']: Parse and analyze Cobalt Strike Malleable C2 profiles with dissect.cobaltstrike (profiles and beacon-payload configs) an
- `Anthropic-Cybersecurity-Skills--analyzing-command-and-control-communication` ['c2', 'command-and-control']: 'Analyzes malware C2 communication over HTTP, HTTPS, DNS, and custom
- `Anthropic-Cybersecurity-Skills--analyzing-persistence-mechanisms-in-linux` ['persistence mechanisms']: Scan Linux systems for persistence mechanisms including crontab/systemd entries, LD_PRELOAD injection, shell profile mod
- `Anthropic-Cybersecurity-Skills--analyzing-powershell-empire-artifacts` ['c2']: Detect PowerShell Empire post-exploitation framework artifacts in Windows Script Block Logging (Event ID 4104) and Modul
- `Anthropic-Cybersecurity-Skills--analyzing-ransomware-network-indicators` ['c2']: Identify ransomware-related network indicators, including C2 beaconing patterns, TOR exit node connections, data exfiltr
- `Anthropic-Cybersecurity-Skills--building-adversary-infrastructure-tracking-system` ['c2']: Build an automated adversary infrastructure tracking system in Python (dnspython, python-whois, shodan, networkx) that p
- `Anthropic-Cybersecurity-Skills--conducting-internal-reconnaissance-with-bloodhound-ce` ['privilege escalation']: Conduct internal Active Directory reconnaissance using BloodHound Community Edition's graph database with the SharpHound
- `Anthropic-Cybersecurity-Skills--configuring-ldap-security-hardening` ['credential harvesting']: Hardens LDAP directory services against credential harvesting, LDAP
- `Anthropic-Cybersecurity-Skills--defending-llms-with-guardrails` ['jailbreaks']: Deploys Llama Guard 3 safety classification, NeMo Guardrails programmable dialogue rails, and LLM Guard input/output sca
- `Anthropic-Cybersecurity-Skills--deobfuscating-powershell-obfuscated-malware` ['c2']: Systematically deobfuscates multi-layer PowerShell malware using AST analysis, dynamic tracing, and tools like PSDecode 
