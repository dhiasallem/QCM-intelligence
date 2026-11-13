import sys

from app.services.ai.orchestrator import generate_quiz, AllProvidersFailed

sys.stdout.reconfigure(encoding="utf-8")

try:
    result = generate_quiz("Informatique", "Bases de données", "Licence 1", 5)
except AllProvidersFailed as e:
    print("ÉCHEC :", e)
    raise SystemExit(1)

print(f"Fournisseur utilisé : {result.provider}")
for a in result.attempts:
    print(f"  - {a.provider} : {'OK' if a.success else 'ÉCHEC'} en {a.duration_ms} ms {a.error or ''}")

print(f"\n{len(result.quiz.questions)} questions valides :\n")
for i, q in enumerate(result.quiz.questions, 1):
    print(f"{i}. [{q.difficulte}] {q.enonce}")
    for o in q.options:
        print(f"   {'✔' if o.correcte else '-'} {o.texte}")
    print()