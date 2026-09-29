"""BEFORE MEMORY -> STORE MEMORY -> AFTER MEMORY demo.
Run: python demo.py            (uses Hindsight server if reachable)
     MEMORY_BACKEND=local python demo.py   (offline)
"""
from memory import Contact, MeetingRecord, retain_memory, recall_memory
from memory.prep import generic_prep, personalized_prep

sarah = Contact("Sarah", "Product Manager", "ABC")

print("=" * 60, "\nBEFORE MEMORY (generic preparation)\n", "=" * 60)
print(generic_prep(sarah))

m1 = MeetingRecord(
    date="2026-09-01",
    topics=["onboarding", "pricing"],
    preferences=["prefers data-driven decisions"],
    promises_made=["send the analytics report"],
    unresolved=["pricing discussion remains unresolved"],
)
print("\n" + "=" * 60, "\nSTORE MEMORY\n", "=" * 60)
print("Retained into bank:", retain_memory(sarah, m1))

print("\n" + "=" * 60, "\nAFTER MEMORY (personalized preparation)\n", "=" * 60)
print(personalized_prep(sarah, recall_memory(sarah)))
