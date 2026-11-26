# Bônus — CI/CD para Dados com GitHub Actions

Depois de concluir os quatro módulos, transforme o que você construiu em um
pipeline **ETL** automatizado: extrair os dados, transformá-los e entregar um
resultado validado. Use o GitHub Copilot para implementar o script e o workflow
a partir deste roteiro — a solução não vem pronta.

## O que você vai praticar

- **Integração contínua (CI):** verificar os módulos e validar o pipeline a
  cada mudança relevante no repositório.
- **Entrega contínua:** disponibilizar o resultado do ETL após as verificações,
  sem fazer deploy de modelos ou dashboards em produção.
- Reutilizar funções, explicitar regras de qualidade e observar falhas.
- Criar um GitHub Actions e consultar seus resultados no github.com.

Não há integração com bancos, APIs de dados ou serviços externos. O dataset é
local e os resultados ficam no GitHub. O runner ainda precisa baixar o código,
as actions e as dependências Python; não se trata de execução offline.

## Como entregar os dados sem integração externa?

| Recurso | Uso neste bônus | Onde consultar |
| --- | --- | --- |
| **Job Summary** | Relatório Markdown com métricas do ETL e tabela por variedade | Página de resumo da execução |
| **Artifact** | CSV completo para download e reutilização | Seção **Artifacts** da execução |
| **Logs** | Etapas, contagens de limpeza e mensagens de erro | Steps do job |

Essa combinação torna o resultado legível e baixável. Logs ajudam a investigar,
mas não substituem um CSV. Arquivos deixados apenas no runner desaparecem ao
final do job; artifacts preservam a saída pelo período de retenção configurado,
não permanentemente. Nenhum desses recursos exige criar secrets neste exercício.

## Pré-requisitos

1. Conclua SQL, pandas, EDA e visualização no seu repositório do workshop.
2. Tenha GitHub Actions habilitado e permissão para enviar alterações.
3. Use Python 3.12 e as dependências de [requirements.txt](../requirements.txt).
4. Na raiz do repositório, execute:

   ```bash
   python -m pip install -r lab/requirements.txt
   python lab/check.py --module all
   ```

Só avance com os quatro módulos passando. O
[check.py](../check.py) verifica esses pré-requisitos; ele não possui um módulo
`bonus` nem valida as novas regras do ETL.

## Passo a passo

### 1. Desenhe o ETL e identifique o que reutilizar

Use [train_sample.csv](../data/train_sample.csv): 1.000 registros com `name`,
`region`, `variety`, `rating` e `notes`.

Reaproveite suas implementações, sem copiar a lógica ou alterar seus contratos:

| Etapa | Função existente | Papel no bônus |
| --- | --- | --- |
| Extração | `load_wines` em [transformations.py](../pandas_module/transformations.py) | Ler o CSV |
| Diagnóstico | `missing_values_report` em [analysis.py](../eda_module/analysis.py) | Contar nulos antes e depois da transformação |
| Transformação | `clean_ratings` em [transformations.py](../pandas_module/transformations.py) | Converter ratings e remover os inválidos/nulos |
| Agregação | `rating_stats_by_variety` em [analysis.py](../eda_module/analysis.py) | Obter `count`, `mean`, `min` e `max` por variedade |

**Atenção:** a amostra tem 11 registros com `variety` vazia. `clean_ratings`
trata apenas `rating`; nenhuma das funções anteriores preenche essas variedades.
Sem tratar esse caso, um `groupby` pode deixar registros fora do relatório.

No bônus, acrescente uma transformação pequena: em uma cópia do DataFrame,
remova espaços nas pontas de `variety` e preencha valores nulos ou em branco
com `Unknown`. Esse rótulo significa **variedade não informada**, não uma
variedade descoberta pelo ETL. Registre quantas linhas receberam o rótulo.

Prompt sugerido:

> Examine minhas funções de pandas e EDA e proponha a sequência do ETL usando
> load_wines, missing_values_report, clean_ratings e rating_stats_by_variety.
> Não altere essas funções. Explique por que ainda precisamos tratar variety
> ausente antes da agregação.

### 2. Implemente a extração, transformação e validação

Crie `lab/bonus_module/pipeline.py`. Ele deve:

1. Aceitar `--input`, com padrão `lab/data/train_sample.csv`.
2. Falhar com mensagem clara se o arquivo não existir, se faltarem as cinco
   colunas esperadas ou se a entrada estiver vazia.
3. Registrar a quantidade de linhas lidas e o relatório inicial de nulos.
4. Executar `clean_ratings` e registrar a diferença entre linhas lidas e
   linhas restantes como **ratings removidos**.
5. Tratar `variety` como descrito no passo anterior, sem remover essas linhas.
6. Validar o resultado: não vazio, `rating` numérico, não nulo e finito,
   `variety` sem nulos ou strings em branco.
7. Registrar o relatório final de nulos. Nulos em outras colunas, como `notes`,
   não devem impedir este relatório por variedade.

Converta/remova ratings conforme o contrato já aprendido, mas **nunca
silenciosamente**. Um rating infinito que sobreviver à limpeza deve provocar
falha na validação final. Não invente limites de notas nem remova outliers
automaticamente: ser atípico não significa ser inválido.

Prompt sugerido:

> Crie o pipeline do bônus reutilizando minhas funções existentes. Trabalhe
> sobre cópias, registre as contagens de leitura, ratings removidos e variedades
> preenchidas com Unknown. Valide os dados transformados antes de exportar.
> Erros devem ter mensagem explicativa e terminar o processo com código não zero.
> Não use tratamentos de exceção que escondam falhas.

### 3. Agregue e exporte o resultado

Reutilize `rating_stats_by_variety` sobre os dados transformados. Adapte sua
saída: se `variety` estiver no índice, transforme-a em coluna; selecione e
renomeie `count` e `mean` para este contrato:

| Coluna | Conteúdo |
| --- | --- |
| `variety` | Variedade ou `Unknown` |
| `wine_count` | Quantidade de registros válidos do grupo |
| `avg_rating` | Média de `rating` do grupo |

Ordene por `wine_count` decrescente, com desempate por `variety` crescente.
Antes de salvar, verifique que a soma de `wine_count` corresponde ao total de
linhas após a limpeza, que cada variedade aparece uma única vez e que as médias
são finitas.

Crie a pasta de saída quando necessário e gere:

- `lab/outputs/bonus/summary.csv`: todas as variedades, as três colunas acima,
  UTF-8, sem índice extra e sem arredondar a média antes da exportação.
- `lab/outputs/bonus/summary.md`: título, contagens de entrada/saída/limpeza e
  tabela com as mesmas variedades; exiba as médias com duas casas decimais.

A pasta [outputs/](../outputs/) já é ignorada pelo Git. Não versione os
resultados. Mesma entrada deve gerar os mesmos arquivos: não acrescente
timestamps ao conteúdo. Só gere saídas depois de todas as validações passarem;
uma tentativa com falha não deve reaproveitar saídas antigas como resultado novo.

Prompt sugerido:

> Adapte o resultado da minha rating_stats_by_variety para variety, wine_count
> e avg_rating. Valide a conservação das linhas e exporte CSV e Markdown nos
> caminhos definidos. Gere a tabela Markdown sem adicionar dependências como
> tabulate, escapando caracteres que possam quebrar suas células.

### 4. Execute e confira localmente

Da raiz do repositório:

```bash
python lab/check.py --module all
python -m lab.bonus_module.pipeline
```

Use imports por `lab.pandas_module` e `lab.eda_module`. A execução com `-m`
permite importar a partir da raiz sem adicionar caminhos manualmente a `sys.path`.

Na amostra original, espere **1.000 linhas lidas, zero ratings removidos,
11 variedades preenchidas e nove grupos no resultado**. O grupo `Unknown`
deve conter 11 registros e a soma de `wine_count` deve ser 1.000.

Confira uma média contra os registros de seu grupo, compare CSV e Markdown
e execute novamente para verificar que os arquivos não mudam.

### 5. Crie o workflow do bônus

Crie `.github/workflows/bonus-data.yml`, separado dos workflows de progresso
do workshop. Não reutilize suas permissões de escrita ou integrações com issues.

Conceitos para reconhecer no YAML:

- **Workflow:** a automação definida no arquivo.
- **Evento:** o que dispara a execução.
- **Runner:** a máquina que executa o trabalho.
- **Job:** conjunto de steps executados no runner.
- **Step:** uma action reutilizável ou um comando.

Configure:

1. Nome identificável, por exemplo, **Bônus — ETL de vinhos**.
2. Eventos `push` e `pull_request`, ambos com `paths` para `lab/**` e
   `.github/workflows/bonus-data.yml`. Assim, mudanças nos módulos, dados,
   dependências ou validador também disparam a verificação.
3. `workflow_dispatch` para execução manual.
4. `permissions: contents: read`, um job em `ubuntu-latest` e steps nomeados.
5. Checkout com `actions/checkout`, Python 3.12 com `actions/setup-python` e
   instalação usando `python -m pip install -r lab/requirements.txt`.
6. Verificação dos quatro módulos, seguida da execução do ETL, com os mesmos
   comandos do passo 4, trabalhando na raiz do repositório.

Prompt sugerido:

> Gere o workflow bonus-data.yml conforme este roteiro. Use actions mantidas
> pelo GitHub em versões suportadas, permissões mínimas e steps nomeados.
> Execute check.py --module all antes de python -m lab.bonus_module.pipeline.
> Se qualquer comando falhar, interrompa a entrega. Não use continue-on-error,
> secrets, integrações externas ou publicação de comentários.

### 6. Publique o resumo e o CSV somente após sucesso

Após o ETL, adicione um step para anexar o relatório ao Job Summary:

```bash
cat lab/outputs/bonus/summary.md >> "$GITHUB_STEP_SUMMARY"
```

Esse comando pertence ao workflow, não à execução local. `GITHUB_STEP_SUMMARY`
é o caminho de um arquivo fornecido pelo Actions; escrever Markdown nele
publica o conteúdo na página de resumo quando o job termina. Não confunda esse
recurso com `GITHUB_OUTPUT`, que serve para passar valores entre steps.

Depois, use `actions/upload-artifact` para publicar **apenas**
`lab/outputs/bonus/summary.csv`, com:

- `name: bonus-wine-summary`;
- `if-no-files-found: error`, para não aceitar exportação ausente;
- `retention-days: 7`, respeitando o limite da política do repositório.

Mantenha a condição padrão de sucesso para os steps de publicação. Não use
`always()` para publicar resultados que dependem de dados válidos.

### 7. Execute e veja os resultados no github.com

1. Revise o código com o Copilot e confira o diff antes de aceitar sugestões.
2. Faça commit e push do script e workflow em uma branch do seu repositório.
   Abra um pull request para também observar a execução por esse evento.
3. Abra **Actions → Bônus — ETL de vinhos → execução**.
4. Confira o status dos jobs e a tabela na página de **Summary** da execução.
5. Abra o job e expanda os steps para consultar contagens e erros nos logs.
6. Na seção **Artifacts** da execução, baixe `bonus-wine-summary`, extraia o
   arquivo e confira o CSV. É necessário estar autenticado e ter acesso ao
   repositório para baixar artifacts.
7. Para usar **Run workflow**, o arquivo com `workflow_dispatch` precisa estar
   na branch padrão. Depois de integrá-lo, selecione a branch e execute novamente.

### 8. Provoque uma falha e demonstre a recuperação

Não altere o dataset versionado. Crie uma cópia temporária em
`lab/outputs/bonus/invalid_input.csv` e remova a coluna `rating` dessa cópia.

```bash
python -m lab.bonus_module.pipeline --input lab/outputs/bonus/invalid_input.csv
```

A execução deve explicar qual coluna falta e terminar com código não zero.
Teste também uma cópia com todos os ratings inválidos: após a limpeza, o ETL
deve falhar por não restarem registros válidos, sem exportar um novo resultado.

Para observar o bloqueio no GitHub, em uma branch de teste altere temporariamente
o comando do ETL no workflow para usar um arquivo inexistente, por exemplo
`--input lab/data/does-not-exist.csv`. Faça push: o job deve ficar vermelho,
os logs devem explicar a falha e os steps de publicação devem ser pulados.
Consulte **essa execução**, não artifacts de uma execução anterior.

Restaure o comando padrão e faça novo push. Verifique a execução verde,
o resumo e o CSV. Exclua a cópia temporária criada para o teste local.

Prompt sugerido:

> Revise meu ETL e workflow: a limpeza está registrada? As validações ocorrem
> antes da exportação? Uma falha impede o resumo e o upload? Use /explain para
> explicar o bloqueio e /fix para corrigir a causa, sem mascarar o erro.

## Critérios de conclusão

- Os quatro módulos passam no validador, localmente e no workflow.
- O ETL reutiliza as funções anteriores e registra as transformações.
- As 11 variedades ausentes da amostra aparecem como `Unknown`, sem perda
  silenciosa de registros na agregação.
- Push, pull request e execução manual funcionam conforme os filtros.
- Uma execução bem-sucedida tem tabela no Job Summary e CSV baixável.
- Uma entrada inválida gera falha explícita e impede a entrega.
- Após corrigir a causa, uma nova execução entrega novamente dados válidos.

## Referências

- [Job Summary e comandos do workflow](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands#adding-a-job-summary)
- [Armazenar e compartilhar dados com artifacts](https://docs.github.com/en/actions/tutorials/store-and-share-data)
- [Executar workflows manualmente](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)
