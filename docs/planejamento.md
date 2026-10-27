# Planejamento e registro das investigações

> Preencha este documento **antes** de usar o LLM (Seção 1), depois registre a
> revisão feita pelo modelo (Seção 2) e, por fim, as três investigações (Seção 3).
> Ele serve de base para o relatório técnico de 4 a 6 páginas.

---

## 1. Planejamento inicial (sem o apoio do LLM)

> Estratégia proposta pelo próprio grupo, registrada antes de consultar o modelo.

- **Aspectos da aplicação a investigar:**
- **Hipóteses iniciais:**
- **Ferramentas que podem contribuir:**
- **Evidências necessárias para sustentar as conclusões:**

## 2. Revisão do planejamento pelo LLM

> Depois de registrar a estratégia acima, peça ao modelo para revisá-la.

| Sugestão do modelo | Decisão (aceita/modificada/rejeitada) | Justificativa técnica |
|--------------------|----------------------------------------|------------------------|
|                    |                                        |                        |

---

## 3. As três investigações

Cenários sugeridos pelo enunciado (escolha três situações distintas):
reconhecimento/enumeração · autenticação/autorização · tratamento de entradas,
requisições ou acesso a recursos.

Para cada investigação, preencha os seis itens. Uma hipótese **refutada com
evidência** também é um resultado válido.

### Investigação 1 — <título>

1. **Hipótese inicial** (o que investigar e por quê):
2. **Estratégia proposta** (como o grupo faria o teste):
3. **Contribuição do agente** (ações/ferramentas sugeridas pelo modelo):
4. **Execução** (ações efetivamente realizadas e resultados obtidos):
5. **Intervenção humana** (decisões aceitas, modificadas ou rejeitadas):
6. **Conclusão** (o que as evidências permitem afirmar e limitações):

- Registro correspondente: `logs/session-________.jsonl`

### Investigação 2 — <título>

1. **Hipótese inicial:**
2. **Estratégia proposta:**
3. **Contribuição do agente:**
4. **Execução:**
5. **Intervenção humana:**
6. **Conclusão:**

- Registro correspondente: `logs/session-________.jsonl`

### Investigação 3 — <título>

1. **Hipótese inicial:**
2. **Estratégia proposta:**
3. **Contribuição do agente:**
4. **Execução:**
5. **Intervenção humana:**
6. **Conclusão:**

- Registro correspondente: `logs/session-________.jsonl`

---

## 4. Análise crítica da utilização da IA

- Em quais situações o modelo apresentou sugestões tecnicamente adequadas?
- O agente selecionou ferramentas coerentes com os objetivos dos testes?
- Os resultados obtidos influenciaram as decisões seguintes do modelo?
- O modelo apresentou interpretações incorretas ou conclusões sem evidências?
- Houve ações repetitivas, desnecessárias ou inadequadas?
- Em quais situações a intervenção humana foi necessária?
- Quais limitações foram observadas no modelo e na integração?

**Exemplo concreto de limitação/erro/dificuldade** (obrigatório):
_como o grupo identificou o problema e como lidou com ele._

**Comparação** entre a estratégia inicial do grupo (Seção 1) e as contribuições do
agente (Seção 3): _possibilidades e limites do uso do LLM nos testes._
