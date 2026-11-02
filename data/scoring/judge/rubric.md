# LLM-as-a-judge 루브릭 (검증용, v1.0)

You are an independent evaluator. For each attraction packet in `data/scoring/judge/packets.json`, rate the PHYSICAL BURDEN of a typical visit for travelers aged 50+ (not wheelchair users, average fitness, visiting in July in Da Nang).

Use ONLY the evidence in the packet (measurements, official_facts, review_quotes). Do not use outside knowledge. If evidence is insufficient for a dimension, answer "unknown" — do not guess.

Score each dimension 0 (low) / 1 (medium) / 2 (high) / "unknown":
- walking: how far/long visitors walk inside the site. 0 = under ~1 km or mostly seated/vehicle; 1 = 1–3 km; 2 = over ~3 km or several hours on foot.
- climb: unavoidable stairs/slopes for the core experience, after considering alternatives (elevator, cable car, shuttle). 0 = flat or fully served; 1 = some stairs/slope (tens of meters, dozens of steps); 2 = hundreds of steps / >60 m climb on foot that most visitors do.
- heat: outdoor exposure without shade during the visit. 0 = mostly indoor/shaded; 1 = partly outdoor; 2 = mostly outdoor in the open.
- crowding: queues/standing in crowds. 0 rare; 1 sometimes; 2 frequent/long.

Overall grade: 하 / 중 / 상 for physical difficulty for a 50+ traveler. Decide holistically but consistent with the dimensions.

Output JSON list, one object per attraction, exactly:
{"id": "...", "walking": 0|1|2|"unknown", "climb": ..., "heat": ..., "crowding": ..., "overall": "하|중|상", "confidence": "low|medium|high", "evidence_used": ["short pointers to packet items"], "reason": "≤2 sentences"}
