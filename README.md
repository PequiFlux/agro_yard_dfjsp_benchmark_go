# Agro Yard D-FJSP GO Benchmark v1.1.0-observed

Esta é a **release oficial** atualmente publicada nesta raiz. Ela foi gerada com **ChatGPT 5.4 PRO** a partir do benchmark nominal `v1.0.0`, depois auditada e revalidada localmente antes de substituir a versão antiga nesta árvore.

Além de release oficial, esta base está agora declarada como o **dataset pai congelado para geração de novas instâncias com modelos da família G2MILP**.

## O que esta release faz

O objetivo da `v1.1.0-observed` não é mudar o problema de otimização, e sim reduzir o aspecto excessivamente "limpo" do dado sintético nominal. A ideia é manter o benchmark reproduzível, rastreável e compatível com Gurobi, mas com uma camada observacional mais próxima do ruído e da persistência que aparecem em sistemas reais.

Em termos de engenharia de dados, os **únicos campos centrais alterados** foram:

- `jobs.csv::completion_due_min`
- `eligible_machines.csv::proc_time_min`

Depois disso, a release recalculou:

- `fifo_schedule.csv`
- `fifo_job_metrics.csv`
- `fifo_summary.json`
- `catalog/benchmark_catalog.csv`
- `catalog/instance_family_summary.csv`

## O que foi preservado

Esta release preserva a estrutura do problema original:

- mesmas 36 instâncias
- mesmas 4 operações obrigatórias por job
- mesmas precedências
- mesma elegibilidade estrutural de máquina por operação
- mesma compatibilidade por commodity
- mesmas janelas de indisponibilidade de máquina
- mesmo esquema de eventos de chegada e visibilidade
- mesma interface de consumo para Gurobi

Em outras palavras: o benchmark continua sendo o mesmo problema D-FJSP calibrado; o que muda é a camada observacional dos prazos e dos tempos de processamento.

## Proveniência registrada

Esta release foi documentada como:

- derivada do release nominal `v1.0.0`
- gerada com **ChatGPT 5.4 PRO**
- integrada e revalidada localmente em `2026-03-27`

Os arquivos de proveniência e rastreabilidade mais importantes são:

- `manifest.json`
- `catalog/observed_noise_manifest.json`
- `docs/observed_noise_model.md`
- `catalog/noise_diagnostics_before_after.json`
- `catalog/noise_validation_summary.md`
- `docs/g2milp_generation_contract.md`
- `catalog/g2milp_generation_contract.json`

## Papel desta base para G2MILP

Esta release deve ser tratada como a referência oficial para gerar datasets filhos com G2MILP. Isso significa:

- esta raiz é o dataset pai congelado
- novas instâncias devem preservar linhagem explícita para `v1.1.0-observed`
- filhos G2MILP não devem sobrescrever esta base
- toda derivação deve carregar manifesto próprio com seed, versão do modelo e escopo da transformação

Os contratos de derivação ficaram registrados em:

- `docs/g2milp_generation_contract.md`
- `catalog/g2milp_generation_contract.json`

## Formulação resumida

As equações detalhadas e a tabela completa de hiperparâmetros estão em `docs/observed_noise_model.md`. Abaixo está a formulação metodológica resumida da camada observacional.

### 1. Prazo observado por job

O prazo observado mantém a prioridade como componente dominante, mas deixa de tratá-la como mecanismo determinístico único:

```text
slack_obs_j =
    b(priority_j)
  + f(appointment_j, commodity_j, moisture_j, shift_j, regime)
  + u_inst
  + u_shift(j)
  + eps_j
```

Depois disso:

```text
due_obs_j = arrival_j + clip(slack_obs_j, LB_j + 18, b(priority_j) + 120)
```

Restrições importantes:

- `lower_j = nominal_processing_lb(j) + 18`
- `upper_j = base(priority_j) + 120`
- `eps_j` é ruído Student-t com escala dependente do regime

### 2. Tempo observado por tripla `(job, op, machine)`

O tempo observado parte do valor nominal e injeta efeitos persistentes e ruído idiossincrático:

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

- `g_j` é o proxy contínuo de congestionamento obtido das chegadas por kernel triangular
- `pause_jom` representa microparadas ocasionais
- o efeito log-multiplicativo é truncado para evitar explosões artificiais

Em termos práticos, a estrutura do benchmark foi preservada e apenas `jobs.csv::completion_due_min` e `eligible_machines.csv::proc_time_min` foram alterados como campos centrais.

## Trilha de auditoria

Cada instância recebeu arquivos para rastrear a transformação linha a linha:

- `job_noise_audit.csv`
- `proc_noise_audit.csv`
- `job_congestion_proxy.csv`
- `noise_manifest.json`

No nível do release:

- `catalog/observed_noise_manifest.json`
- `catalog/validation_report_observed.csv`
- `catalog/noise_diagnostics.json`
- `catalog/noise_diagnostics_before_after.json`
- `catalog/noise_validation_summary.md`

Isso permite responder, para qualquer linha alterada, de onde veio o valor observado e quais componentes participaram da transformação.

Uma checagem manual direta é:

1. conferir em `job_noise_audit.csv` que `completion_due_observed_min` coincide com `jobs.csv::completion_due_min`
2. conferir em `proc_noise_audit.csv` que `proc_time_observed_min` coincide com `eligible_machines.csv::proc_time_min`

## Como validamos se a release era válida ou não

Aqui o critério não foi "parece razoável"; foi um conjunto de testes reproduzíveis.

### 1. Integridade estrutural

Rodamos:

```bash
python tools/validate_observed_release.py .
```

Resultado local após integração:

- `36/36` instâncias com `PASS`
- nenhum caso de job sem 4 operações
- nenhuma precedência inconsistente
- nenhuma operação sem máquina elegível
- nenhum prazo abaixo do lower bound plausível
- nenhum overlap de máquina no baseline FIFO
- nenhuma inconsistência entre `eligible_machines.csv`, `fifo_schedule.csv` e `fifo_job_metrics.csv`

O relatório está em:

- `catalog/validation_report_observed.csv`

### 2. Reconciliação nominal vs observado

O release só é aceitável se os valores observados coincidirem exatamente com os arquivos centrais:

- `job_noise_audit.csv::completion_due_observed_min` deve bater com `jobs.csv::completion_due_min`
- `proc_noise_audit.csv::proc_time_observed_min` deve bater com `eligible_machines.csv::proc_time_min`

Se essa reconciliação falhar, a release deixa de ser auditável e deve ser tratada como inválida.

### 3. Redução de sobre-determinismo

O objetivo não era injetar ruído aleatório qualquer, e sim reduzir dependências excessivamente perfeitas sem destruir a semântica do benchmark.

Os diagnósticos agregados do release mostraram:

- `R²(due slack ~ priority)` caiu de `1.0000` para `0.4848`
- `R²(proc UNLOAD ~ load + machine + moisture)` caiu de `0.7540` para `0.4995`

Esses resultados estão em:

- `catalog/noise_diagnostics_before_after.json`

Se esses valores não caíssem, a camada observacional não teria cumprido seu papel. Se caíssem de forma caótica junto com perda de coerência operacional, a release também seria rejeitada.

### 4. Sanidade comportamental por regime

Mesmo com o ruído observacional, as famílias de instância continuaram obedecendo à ordem operacional esperada:

- `balanced < peak < disrupted` em `avg_fifo_mean_flow_min`
- `balanced < peak < disrupted` em `avg_fifo_p95_flow_min`

Isso aparece em:

- `catalog/instance_family_summary.csv`

Esse ponto importa porque uma release "menos determinística" mas que destrói a hierarquia dos regimes deixa de ser útil como benchmark.

### 5. Validação de promoção para release oficial

Depois da promoção desta release para a raiz do projeto, revalidamos diretamente a nova raiz:

```bash
python tools/validate_observed_release.py .
python gurobi/load_instance.py instances/GO_XS_BALANCED_01
```

Esses comandos executaram com sucesso na raiz promovida, o que confirma que a release oficial permaneceu carregável e estruturalmente válida após substituir a versão antiga.

## Quando considerar esta release inválida

Esta release deve ser tratada como inválida se qualquer um dos pontos abaixo ocorrer:

- alguma instância falhar na validação estrutural
- os audits não reconciliarem exatamente com `jobs.csv` e `eligible_machines.csv`
- a ordem `balanced < peak < disrupted` colapsar nas métricas de fluxo
- os diagnósticos não mostrarem redução de sobre-determinismo
- a promoção quebrar o carregamento via `gurobi/load_instance.py`

## Por que isso é útil para testes mais próximos de problemas reais

Esta release continua sendo sintética, então ela **não** substitui logs operacionais reais. Mesmo assim, ela é muito mais útil do que uma base puramente nominal para testar métodos com ambição de uso em ambiente real, por cinco razões.

- Ela introduz heterogeneidade intraclasse sem perder rastreabilidade.
- Ela preserva efeitos persistentes de máquina, turno, regime e congestionamento, que são exatamente o tipo de sinal que costuma aparecer em operação.
- Ela permite testar robustez de modelos exatos, metaheurísticas e políticas de rescheduling contra dados menos "perfeitos".
- Ela mantém compatibilidade com o ecossistema de benchmark e com os artefatos do baseline, então a comparação entre métodos continua limpa.
- Ela facilita análise de falhas, porque cada valor observado pode ser auditado linha a linha.

Na prática, isso torna a `v1.1.0-observed` especialmente útil para:

- experimentos de robustez antes de um piloto com dado real
- comparação entre políticas sob regime `balanced`, `peak` e `disrupted`
- avaliação de heurísticas sensíveis a ruído e congestionamento
- estudo de estabilidade de soluções quando o benchmark deixa de ser perfeitamente determinístico
- demonstração metodológica, no TCC, de que o benchmark não depende apenas de regras "limpas"

## Limite metodológico

O ganho de realismo aqui é importante, mas limitado:

- esta base ainda é sintética
- a camada observacional não prova validade externa forte
- ela melhora o teste de robustez e plausibilidade, mas não substitui calibração final com logs de uma unidade real

O uso correto desta release é como **ponte metodológica** entre o benchmark nominal totalmente controlado e cenários de implantação em problemas do mundo real.

## Arquivos mais importantes

- `docs/observed_noise_model.md`: formulação técnica detalhada e hiperparâmetros
- `catalog/observed_noise_manifest.json`: manifesto do modelo observacional no nível do release
- `catalog/noise_diagnostics_before_after.json`: comparação antes/depois dos diagnósticos de determinismo
- `catalog/validation_report_observed.csv`: status estrutural das 36 instâncias
- `catalog/noise_validation_summary.md`: resumo executivo da validação

## Comandos úteis

Validar a release oficial:

```bash
python tools/validate_observed_release.py .
```

Abrir a análise exploratória completa em modo REPL:

```bash
python -i tools/instance_analysis_repl.py
```

No REPL, os objetos e helpers principais já ficam carregados:

- `SUMMARY`
- `inventory_tables()`
- `validation_tables()`
- `plot_inventory_overview()`
- `plot_validation_overview()`
- `plot_observational_layer()`
- `plot_operational_sanity()`
- `plot_instance_drilldown('GO_XS_DISRUPTED_01')`
- `export_all_artifacts()`

Os artefatos exportados pelo REPL são gravados em:

- `output/repl-analysis-artifacts/`
