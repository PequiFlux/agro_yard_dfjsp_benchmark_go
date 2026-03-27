# Agro Yard D-FJSP GO Benchmark v1.1.0-observed

Esta é a release oficial do benchmark em sua forma **observada**. Ela foi derivada do release nominal `v1.0.0` com **ChatGPT 5.4 PRO**, auditada e revalidada localmente, e deve ser tratada como o **dataset seed oficial** para futuras gerações com modelos da família **G2MILP**.

## O que muda

Os únicos campos centrais alterados foram:

- `jobs.csv::completion_due_min`
- `eligible_machines.csv::proc_time_min`

Depois disso, foram recalculados:

- `fifo_schedule.csv`
- `fifo_job_metrics.csv`
- `fifo_summary.json`
- `catalog/benchmark_catalog.csv`
- `catalog/instance_family_summary.csv`

## O que foi preservado

- as mesmas `36` instâncias
- exatamente `4` operações por job
- as precedências estruturais
- a elegibilidade estrutural de máquina por operação
- a compatibilidade por commodity
- as janelas de indisponibilidade de máquina
- os eventos de chegada e visibilidade
- a interface de consumo do benchmark pelo stack Gurobi

Em outras palavras: o problema continua sendo o mesmo benchmark D-FJSP; o que mudou foi a camada observacional dos prazos e dos tempos de processamento.

## Fórmulas usadas

### 1. Prazo observado por job

$$
\operatorname{slack}^{obs}_j =
b(\operatorname{priority}_j)
+ f(\operatorname{appointment}_j,\operatorname{commodity}_j,\operatorname{moisture}_j,\operatorname{shift}_j,\operatorname{regime})
+ u_{\operatorname{inst}}
+ u_{\operatorname{shift}(j)}
+ \varepsilon_j
$$

$$
\operatorname{due}^{obs}_j =
\operatorname{arrival}_j +
\operatorname{clip}\!\left(
\operatorname{slack}^{obs}_j,\,
LB_j + 18,\,
b(\operatorname{priority}_j) + 120
\right)
$$

Onde:

- $b(\operatorname{priority}_j)$ é a folga base por classe de prioridade
- $f(\cdot)$ agrega efeitos fixos pequenos e interpretáveis
- $u_{\operatorname{inst}}$ é um efeito latente da instância
- $u_{\operatorname{shift}(j)}$ é um efeito latente do turno
- $\varepsilon_j$ é ruído Student-t com escala dependente do regime
- $LB_j$ é o lower bound físico plausível do job, calculado como a soma dos menores tempos elegíveis de suas quatro operações

### 2. Tempo observado por tripla `(job, op, machine)`

$$
p^{obs}_{jom} =
\max\!\left(
p^{\min}_{\operatorname{stage}},
\operatorname{round}\!\left(
p^{nom}_{jom}\cdot
\exp\!\left(
u_m
+ u_{\operatorname{shift}}
+ u_{\operatorname{stage,inst}}
+ u_{\operatorname{regime}}
+ \beta_{\operatorname{stage}}\, g_j
+ u_{\operatorname{commodity}}
+ u_{\operatorname{moisture}}
+ \varepsilon_{jom}
\right)
+ \operatorname{pause}_{jom}
\right)
\right)
$$

Onde:

- $p^{nom}_{jom}$ é o tempo nominal original
- $u_m$ é um efeito persistente da máquina
- $u_{\operatorname{shift}}$ é um efeito do turno
- $u_{\operatorname{stage,inst}}$ é um efeito latente do estágio na instância
- $u_{\operatorname{regime}}$ captura o ambiente `balanced / peak / disrupted`
- $g_j$ é o proxy contínuo de congestionamento derivado das chegadas
- $u_{\operatorname{commodity}}$ e $u_{\operatorname{moisture}}$ são ajustes semânticos pequenos
- $\varepsilon_{jom}$ é ruído idiossincrático
- $\operatorname{pause}_{jom}$ representa microparadas ocasionais
- $p^{\min}_{\operatorname{stage}}$ impõe um piso por estágio

## Como validamos

### 1. Integridade estrutural

Rodamos:

```bash
python tools/validate_observed_release.py .
```

Resultado da release oficial:

- `36/36` instâncias com `PASS`
- todo job tem `4` operações
- todo job tem `3` precedências estruturais
- toda operação tem ao menos uma máquina elegível
- todo prazo respeita `completion_due_min - arrival_time_min >= nominal_lb + 18`
- cada job tem exatamente `1` evento `JOB_VISIBLE`
- cada job tem exatamente `1` evento `JOB_ARRIVAL`
- não há overlap de máquina no baseline FIFO
- `end_min - start_min` bate com `eligible_machines.csv::proc_time_min`
- `fifo_job_metrics.csv` bate com `fifo_schedule.csv`

### 2. Validação do loader Gurobi

Rodamos:

```bash
python tools/validate_benchmark.py
python gurobi/load_instance.py instances/GO_XS_BALANCED_01
```

Isso garante que:

- a instância continua carregável pelo loader
- toda `machine_id` referenciada existe em `machines.csv`
- todo `proc_time_min` é positivo
- todo par `(job_id, op_seq)` continua com elegibilidade válida

### 3. Reconciliação dos audits

A release só é aceitável se:

- `job_noise_audit.csv::completion_due_observed_min == jobs.csv::completion_due_min`
- `proc_noise_audit.csv::proc_time_observed_min == eligible_machines.csv::proc_time_min`

### 4. Diagnósticos de realismo

Os diagnósticos agregados da release foram:

- `R²(due slack ~ priority): 1.0000 -> 0.4848`
- `R²(proc UNLOAD ~ load + machine + moisture): 0.7540 -> 0.4995`

Além disso, a ordem operacional esperada foi preservada:

- `balanced < peak < disrupted` em `avg_fifo_mean_flow_min`
- `balanced < peak < disrupted` em `avg_fifo_p95_flow_min`

## Resultados do notebook

O notebook `output/jupyter-notebook/instance-validation-and-exploratory-analysis.ipynb` gerou uma camada adicional de testes, estatísticas e figuras sobre as `36` instâncias oficiais.

Resumo dos resultados agregados:

- `structural_pass_rate = 1.0000`
- `due_audit_match_share = 1.0000`
- `proc_audit_match_share = 1.0000`
- `all_regime_order_checks_pass = True`
- soma total de mismatches em eventos: `0` para `JOB_VISIBLE`, `JOB_ARRIVAL`, `MACHINE_DOWN` e `MACHINE_UP`
- margem observada sobre o lower bound físico no resumo por escala/regime: de `124` a `353` minutos

Artefatos tabulares principais:

- `output/jupyter-notebook/instance_validation_analysis_artifacts/notebook_summary.csv`
- `output/jupyter-notebook/instance_validation_analysis_artifacts/structural_report.csv`
- `output/jupyter-notebook/instance_validation_analysis_artifacts/audit_reconciliation.csv`
- `output/jupyter-notebook/instance_validation_analysis_artifacts/event_report.csv`
- `output/jupyter-notebook/instance_validation_analysis_artifacts/due_margin_summary.csv`

Imagens principais:

![Structural validation and auditability](output/jupyter-notebook/instance_validation_analysis_artifacts/structural_validation_and_auditability.png)

![Observational layer behavior](output/jupyter-notebook/instance_validation_analysis_artifacts/observational_layer_behavior.png)

![Operational performance and regime sanity](output/jupyter-notebook/instance_validation_analysis_artifacts/operational_performance_and_regime_sanity.png)

![FIFO schedule drilldown for GO_XS_DISRUPTED_01](output/jupyter-notebook/instance_validation_analysis_artifacts/go_xs_disrupted_01_fifo_schedule.png)

O drilldown FIFO acima foi regenerado na versão atual do notebook com menos rótulos, destaque explícito de downtime e separação visual mais limpa entre as faixas de máquina. O arquivo `.ipynb` salvo no repositório já contém essa saída embutida.

Figuras complementares:

- `output/jupyter-notebook/instance_validation_analysis_artifacts/inventory_overview.png`
- `output/jupyter-notebook/instance_validation_analysis_artifacts/congestion_diagnostics.png`
- `output/jupyter-notebook/instance_validation_analysis_artifacts/go_xs_disrupted_01_job_level_views.png`

## Arquivos principais

- `manifest.json`
- `docs/observed_noise_model.md`
- `catalog/observed_noise_manifest.json`
- `catalog/noise_diagnostics_before_after.json`
- `catalog/validation_report_observed.csv`
- `docs/g2milp_generation_contract.md`
- `output/jupyter-notebook/instance-validation-and-exploratory-analysis.ipynb`
- `output/jupyter-notebook/instance_validation_analysis_artifacts/`

## Leitura correta desta base

Esta base continua sendo sintética. O ganho aqui não é “virar dado real”, e sim sair de um benchmark excessivamente limpo para um dataset seed mais útil para testes de robustez, comparação de métodos e geração futura de instâncias com G2MILP, sem perder rastreabilidade.
