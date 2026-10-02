"""Project Templates for Juvion (Modelos de Obra).

Provides structured templates for:
- Conto (Short Story)
- Romance (Classic 3-Act Novel)
- Fantasia & Ficção (Worldbuilding, Magic Rules, Epic Structure)
- Mistério & Suspense (Hook, Clues, Red Herrings, Reveal)
- Serial & Webnovel (Arcs, Cliffhangers, Episodic Beats)

Includes acts, chapters, scenes with craft summaries, and initial universe entries.
"""

import uuid


TEMPLATES = {
    "novel": {
        "id": "novel",
        "name": "Romance (Estrutura clássica em 3 Atos)",
        "genre": "Romance",
        "word_goal": 80_000,
        "description": "Estrutura equilibrada em Três Atos com apresentação do mundo comum, incidente incitante, ponto de virada, clímax e resolução.",
        "categories": "Ficção, Romance, Drama",
        "tags": "jornada do herói, 3 atos, arco de personagem",
        "structure": {
            "acts": [
                {
                    "name": "Ato 1 — Apresentação e Ruptura",
                    "summary": "Estabelece o status quo, introduz o protagonista, o tema e o incidente incitante que quebra a rotina.",
                    "chapters": [
                        {
                            "name": "Capítulo 1: O Mundo Comum",
                            "summary": "Apresentação da vida diária, anseios e a grande carência interna do protagonista.",
                            "scenes": [
                                {"name": "Cena 1: A Rotina e o Incômodo"},
                                {"name": "Cena 2: O Chamado / Incidente Incitante"}
                            ]
                        },
                        {
                            "name": "Capítulo 2: A Resistência e o Limiar",
                            "summary": "O protagonista hesita diante da mudança, mas um novo acontecimento o força a cruzar o limiar.",
                            "scenes": [
                                {"name": "Cena 1: A Tentativa de Voltar Atrás"},
                                {"name": "Cena 2: Cruzando o Ponto Sem Retorno"}
                            ]
                        }
                    ]
                },
                {
                    "name": "Ato 2 — Conflito e Revelação",
                    "summary": "A maior parte da narrativa: novos aliados, adversários, testes crescentes, ponto médio de virada e a 'noite escura da alma'.",
                    "chapters": [
                        {
                            "name": "Capítulo 3: Território Desconhecido",
                            "summary": "Primeiros testes no novo ambiente ou na nova jornada.",
                            "scenes": [
                                {"name": "Cena 1: Novos Encontros e Regras"},
                                {"name": "Cena 2: O Primeiro Teste"}
                            ]
                        },
                        {
                            "name": "Capítulo 4: O Ponto Médio (Midpoint)",
                            "summary": "Uma virada crucial: a postura passa de passiva/reativa para ativa.",
                            "scenes": [
                                {"name": "Cena 1: O Falso Sucesso ou Alerta"},
                                {"name": "Cena 2: As Consequências e a Aposta Elevada"}
                            ]
                        },
                        {
                            "name": "Capítulo 5: A Crise e a Derrota Aparente",
                            "summary": "O momento mais sombrio onde tudo parece perdido antes do renascimento da determinação.",
                            "scenes": [
                                {"name": "Cena 1: A Perda Crucial"},
                                {"name": "Cena 2: A Noite Escura da Alma"}
                            ]
                        }
                    ]
                },
                {
                    "name": "Ato 3 — Clímax e Nova Realidade",
                    "summary": "O confronto final onde a lição aprendida é colocada à prova e um novo equilíbrio se forma.",
                    "chapters": [
                        {
                            "name": "Capítulo 6: O Confronto Final",
                            "summary": "As forças antagônicas colidem no clímax decisivo da história.",
                            "scenes": [
                                {"name": "Cena 1: O Plano e a Invasão"},
                                {"name": "Cena 2: O Clímax Decisivo"}
                            ]
                        },
                        {
                            "name": "Capítulo 7: A Resolução",
                            "summary": "O retorno ao lar transformado; as pontas soltas são amarradas.",
                            "scenes": [
                                {"name": "Cena 1: O Pós-Tempestade"},
                                {"name": "Cena 2: O Novo Equilíbrio"}
                            ]
                        }
                    ]
                }
            ]
        },
        "universe": [
            {"name": "Protagonista", "category": "Personagens", "notes": "Ficha do herói/heroína: motivação primária, fraqueza, objetivo externo e necessidade interna."},
            {"name": "Antagonista", "category": "Personagens", "notes": "Força de oposição direta ou rival: filosofia, motivos compreensíveis e recursos."},
            {"name": "Local Principal", "category": "Lugares", "notes": "Cenário primário onde os maiores conflitos se desenrolam."}
        ]
    },
    "short_story": {
        "id": "short_story",
        "name": "Conto (Narrativa Curta e Focada)",
        "genre": "Conto",
        "word_goal": 6_000,
        "description": "Formato concentrado em um único conflito central, poucos personagens, forte unidade de tempo/espaço e impacto no desfecho.",
        "categories": "Ficção Curta, Conto",
        "tags": "conflito único, ritmo ágil, desfecho marcante",
        "structure": {
            "acts": [
                {
                    "name": "Ato Único — Desenvolvimento do Conflito",
                    "summary": "Narrativa compacta que vai direto ao ponto sem subtramas paralelas.",
                    "chapters": [
                        {
                            "name": "Parte 1: A Situação e a Perturbação",
                            "summary": "Entrada rápida na ação, revelando a tensão central imediatamente.",
                            "scenes": [
                                {"name": "Cena 1: O Gancho Inicial"},
                                {"name": "Cena 2: O Agravamento do Conflito"}
                            ]
                        },
                        {
                            "name": "Parte 2: Clímax e Desfecho",
                            "summary": "A tensão atinge o ponto de ruptura e se resolve com força temática ou reviravolta.",
                            "scenes": [
                                {"name": "Cena 1: O Momento Decisivo"},
                                {"name": "Cena 2: A Revelação ou Conclusão"}
                            ]
                        }
                    ]
                }
            ]
        },
        "universe": [
            {"name": "Protagonista", "category": "Personagens", "notes": "Personagem central com uma decisão urgente a tomar."},
            {"name": "Espaço Central", "category": "Lugares", "notes": "Ambiente compacto e sugestivo onde a ação se desenrola."}
        ]
    },
    "fantasy": {
        "id": "fantasy",
        "name": "Fantasia & Worldbuilding Épico",
        "genre": "Fantasia",
        "word_goal": 100_000,
        "description": "Focado em construção de mundos ricos: sistemas de magia/tecnologia, facções, lore ancestral, mapas e jornada com impacto social ou político.",
        "categories": "Fantasia, Ficção Especulativa, Aventura",
        "tags": "worldbuilding, magia, facções, jornada épica",
        "structure": {
            "acts": [
                {
                    "name": "Ato 1 — As Regras do Mundo e a Ruptura",
                    "summary": "Apresentação da cultura, da magia cotidiana e o prenúncio de um cataclismo ou conspiração.",
                    "chapters": [
                        {
                            "name": "Capítulo 1: Sob as Sombras do Passado",
                            "summary": "O mundo funcionando sob as suas leis e crenças habituais.",
                            "scenes": [
                                {"name": "Cena 1: O Rito ou Ofício"},
                                {"name": "Cena 2: O Sinal de Mau Agouro"}
                            ]
                        },
                        {
                            "name": "Capítulo 2: A Quebra do Equilíbrio",
                            "summary": "Um evento mágico ou político abala a segurança conhecida.",
                            "scenes": [
                                {"name": "Cena 1: O Ataque ou Notícia Sombria"},
                                {"name": "Cena 2: A Partida Forçada"}
                            ]
                        }
                    ]
                },
                {
                    "name": "Ato 2 — A Jornada e os Segredos Ancestrais",
                    "summary": "Viagem por diferentes terras, choque de culturas, intrigas de facções e revelação de segredos arcanos.",
                    "chapters": [
                        {
                            "name": "Capítulo 3: Além das Fronteiras",
                            "summary": "A travessia por regiões selvagens ou cidades estrangeiras.",
                            "scenes": [
                                {"name": "Cena 1: O Ermo e seus Perigos"},
                                {"name": "Cena 2: O Santuário ou Encruzilhada"}
                            ]
                        },
                        {
                            "name": "Capítulo 4: Conspirações e Magia Antiga",
                            "summary": "O confronto direto com os métodos e a extensão do poder inimigo.",
                            "scenes": [
                                {"name": "Cena 1: O Segredo Proibido"},
                                {"name": "Cena 2: A Traição ou Emboscada"}
                            ]
                        }
                    ]
                },
                {
                    "name": "Ato 3 — A Batalha pelo Destino",
                    "summary": "Convergência de forças, cerco ou duelo de poderes e o legado que fica para as gerações futuras.",
                    "chapters": [
                        {
                            "name": "Capítulo 5: O Confronto Épico",
                            "summary": "A batalha culminante entre as visões antagônicas do mundo.",
                            "scenes": [
                                {"name": "Cena 1: O Duelo / Batalha Final"},
                                {"name": "Cena 2: O Preço da Vitória"}
                            ]
                        },
                        {
                            "name": "Capítulo 6: As Cinzas e o Renascimento",
                            "summary": "O novo mundo que emerge da transformação.",
                            "scenes": [
                                {"name": "Cena 1: O Novo Pacto"}
                            ]
                        }
                    ]
                }
            ]
        },
        "universe": [
            {"name": "Sistema de Magia / Poder", "category": "Regras", "notes": "Como funciona o poder: custos, limites, quem pode usar e quais as proibições."},
            {"name": "Reino / Cidade Principal", "category": "Lugares", "notes": "Geografia, cultura, governo e clima da região inicial."},
            {"name": "Facção / Ordem Antagônica", "category": "Organizações", "notes": "Credo, hierarquia e ambições do grupo adversário."}
        ]
    },
    "mystery": {
        "id": "mystery",
        "name": "Mistério, Suspense & Investigação",
        "genre": "Mistério",
        "word_goal": 70_000,
        "description": "Estrutura dedutiva clássica: crime ou enigma inicial, cena do crime, coleta de pistas, pistas falsas (red herrings), interrogatórios e grande revelação.",
        "categories": "Mistério, Suspense, Policial, Thriller",
        "tags": "investigação, pistas, suspeitos, plot twist",
        "structure": {
            "acts": [
                {
                    "name": "Ato 1 — O Crime e os Primeiros Suspeitos",
                    "summary": "Descoberta do mistério, exame da cena, delimitação das circunstâncias e motivos iniciais.",
                    "chapters": [
                        {
                            "name": "Capítulo 1: O Corpo / O Enigma",
                            "summary": "A descoberta chocante que coloca a história em movimento.",
                            "scenes": [
                                {"name": "Cena 1: O Chamado do Investigador"},
                                {"name": "Cena 2: A Cena do Crime e a Primeira Pista"}
                            ]
                        },
                        {
                            "name": "Capítulo 2: O Círculo de Suspeitos",
                            "summary": "Mapeamento das pessoas que tinham motivo, meio e oportunidade.",
                            "scenes": [
                                {"name": "Cena 1: Primeiro Interrogatório"},
                                {"name": "Cena 2: Álibis e Inconsistências"}
                            ]
                        }
                    ]
                },
                {
                    "name": "Ato 2 — A Teia de Mentiras e Pistas Falsas",
                    "summary": "Aprofundamento da investigação; pistas contraditórias e o perigo que se volta contra o investigador.",
                    "chapters": [
                        {
                            "name": "Capítulo 3: Segredos Ocultos",
                            "summary": "A descoberta de que a vítima ou os suspeitos não eram quem aparentavam ser.",
                            "scenes": [
                                {"name": "Cena 1: A Pista Falsa (Red Herring)"},
                                {"name": "Cena 2: Um Novo Crime ou Ameaça Direta"}
                            ]
                        },
                        {
                            "name": "Capítulo 4: O Beco Sem Saída",
                            "summary": "A teoria do investigador desaba, forçando-o a reexaminar tudo sob novo ângulo.",
                            "scenes": [
                                {"name": "Cena 1: A Queda da Teoria Principal"},
                                {"name": "Cena 2: O Detalhe que Todos Ignoraram"}
                            ]
                        }
                    ]
                },
                {
                    "name": "Ato 3 — A Dedução e o Confronto Final",
                    "summary": "As peças se encaixam, o verdadeiro culpado é encurralado e o caso é encerrado.",
                    "chapters": [
                        {
                            "name": "Capítulo 5: O Cerco e a Revelação",
                            "summary": "O momento clássico onde a verdade vem à tona.",
                            "scenes": [
                                {"name": "Cena 1: O Confronto com o Culpado"},
                                {"name": "Cena 2: A Confissão ou Tentativa de Fuga"}
                            ]
                        },
                        {
                            "name": "Capítulo 6: O Fechamento do Caso",
                            "summary": "As consequências éticas e emocionais da verdade desvendada.",
                            "scenes": [
                                {"name": "Cena 1: A Resolução da Investigação"}
                            ]
                        }
                    ]
                }
            ]
        },
        "universe": [
            {"name": "Investigador(a)", "category": "Personagens", "notes": "Perfil, método de trabalho, vício ou dilema pessoal."},
            {"name": "A Vítima", "category": "Personagens", "notes": "Quem era, que segredos guardava e quem tinha motivos para silenciá-la."},
            {"name": "A Pista Crucial", "category": "Itens", "notes": "Objeto ou detalhe despercebido que amarra toda a conclusão."}
        ]
    },
    "serial": {
        "id": "serial",
        "name": "Serial & Webnovel (Episódico com Arcos)",
        "genre": "Serial",
        "word_goal": 120_000,
        "description": "Estrutura episódica com ganchos fortes (cliffhangers) no fim de cada capítulo, arcos menores de progressão contínua e forte retenção de leitores.",
        "categories": "Webnovel, Serial, Fantasia Urbana, Ficção em Série",
        "tags": "cliffhanger, progressão, arcos de temporada, serializado",
        "structure": {
            "acts": [
                {
                    "name": "Arco 1 — Despertar e Primeiras Conquistas",
                    "summary": "Arco introdutório onde o protagonista ganha uma nova capacidade, recurso ou missão urgente.",
                    "chapters": [
                        {
                            "name": "Capítulo 1: O Incidente e a Nova Condição",
                            "summary": "Gancho imediato com transformação abrupta da realidade do protagonista.",
                            "scenes": [
                                {"name": "Episódio 1: O Despertar"},
                                {"name": "Episódio 2: O Teste de Sobrevivência (Cliffhanger)"}
                            ]
                        },
                        {
                            "name": "Capítulo 2: Primeiros Ganhos e Reputação",
                            "summary": "O personagem aprende a explorar sua nova posição e atrai atenção indesejada.",
                            "scenes": [
                                {"name": "Episódio 3: O Primeiro Triunfo"},
                                {"name": "Episódio 4: Olhos na Sombra (Cliffhanger)"}
                            ]
                        }
                    ]
                },
                {
                    "name": "Arco 2 — Torneio / Desafio de Ascensão",
                    "summary": "Conflito público ou teste rigoroso contra outros competidores ou facções.",
                    "chapters": [
                        {
                            "name": "Capítulo 3: A Arena ou Seleção",
                            "summary": "Apresentação dos rivais mais fortes e das apostas do arco.",
                            "scenes": [
                                {"name": "Episódio 5: O Sorteio ou Preparação"},
                                {"name": "Episódio 6: O Confronto Inesperado"}
                            ]
                        },
                        {
                            "name": "Capítulo 4: O Clímax da Primeira Temporada",
                            "summary": "Resolução do arco atual, deixando portas abertas para os mistérios do mundo maior.",
                            "scenes": [
                                {"name": "Episódio 7: A Batalha Decisiva"},
                                {"name": "Episódio 8: A Grande Revelação da Temporada"}
                            ]
                        }
                    ]
                }
            ]
        },
        "universe": [
            {"name": "Sistema de Progressão", "category": "Regras", "notes": "Como o protagonista evolui: patamares, recursos, reputação ou rankings."},
            {"name": "Rival do Arco", "category": "Personagens", "notes": "Antagonista local que desafia o protagonista durante a primeira temporada."}
        ]
    }
}


def populate_template_structure(template_data):
    """Deeply clone structure and inject fresh UUIDs for acts, chapters, and scenes."""
    import copy
    raw = copy.deepcopy(template_data["structure"])
    for act in raw.get("acts", []):
        act["uuid"] = str(uuid.uuid4())
        act["has_summary"] = bool(act.get("summary"))
        for chapter in act.get("chapters", []):
            chapter["uuid"] = str(uuid.uuid4())
            chapter["has_summary"] = bool(chapter.get("summary"))
            for scene in chapter.get("scenes", []):
                scene["uuid"] = str(uuid.uuid4())
    return raw


def seed_template_universe(compendium, template_data):
    """Populate the factory categories with the template's optional entries."""
    aliases = {
        "Lugares": ("Worldbuilding", "Lugares"),
        "Regras": ("Sistemas e poderes", "Magia"),
        "Itens": ("Itens e artefatos", "Objetos"),
        "Organizações": ("Organizações", "Facções"),
    }
    for entry in template_data.get("universe", []):
        category, subcategory = aliases.get(entry.get("category"), (entry.get("category", "Narrativa"), ""))
        name = entry.get("name", "Ficha")
        if category == "Personagens":
            subcategory = "Antagonistas" if name in {"Antagonista", "Rival do Arco"} else "Protagonistas" if name in {"Protagonista", "Investigador(a)"} else "Coadjuvantes"
        if not compendium.add_entry(name=name, category_name=category, subcategory_name=subcategory, content=entry.get("notes", "")):
            raise ValueError("Não foi possível criar a ficha do modelo: {}".format(name))
