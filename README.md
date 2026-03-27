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

```text
slack_obs_j =
    b(priority_j)
  + f(appointment_j, commodity_j, moisture_j, shift_j, regime)
  + u_inst
  + u_shift(j)
  + eps_j
```

```text
due_obs_j = arrival_j + clip(slack_obs_j, LB_j + 18, b(priority_j) + 120)
```

Onde:

- `b(priority_j)` é a folga base por classe de prioridade
- `f(.)` agrega efeitos fixos pequenos e interpretáveis
- `u_inst` é um efeito latente da instância
- `u_shift(j)` é um efeito latente do turno
- `eps_j` é ruído Student-t com escala dependente do regime
- `LB_j` é o lower bound físico plausível do job, calculado como a soma dos menores tempos elegíveis de suas quatro operações

### 2. Tempo observado por tripla `(job, op, machine)`

```text
p_obs_jom =
  max(
    p_stage_min,
    round(
      p_nom_jom * exp(
        u_m
      + u_shift
      + u_stage_inst
      + u_regime
      + beta_stage * g_j
      + u_commodity
      + u_moisture
      + eps_jom
      )
      + pause_jom
    )
  )
```

Onde:

- `p_nom_jom` é o tempo nominal original
- `u_m` é um efeito persistente da máquina
- `u_shift` é um efeito do turno
- `u_stage_inst` é um efeito latente do estágio na instância
- `u_regime` captura o ambiente `balanced / peak / disrupted`
- `g_j` é o proxy contínuo de congestionamento derivado das chegadas
- `u_commodity` e `u_moisture` são ajustes semânticos pequenos
- `eps_jom` é ruído idiossincrático
- `pause_jom` representa microparadas ocasionais
- `p_stage_min` impõe um piso por estágio

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

## Arquivos principais

- `manifest.json`
- `docs/observed_noise_model.md`
- `catalog/observed_noise_manifest.json`
- `catalog/noise_diagnostics_before_after.json`
- `catalog/validation_report_observed.csv`
- `docs/g2milp_generation_contract.md`

## Leitura correta desta base

Esta base continua sendo sintética. O ganho aqui não é “virar dado real”, e sim sair de um benchmark excessivamente limpo para um dataset seed mais útil para testes de robustez, comparação de métodos e geração futura de instâncias com G2MILP, sem perder rastreabilidade.
