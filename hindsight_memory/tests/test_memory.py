import os, sys, unittest
os.environ["MEMORY_BACKEND"] = "local"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from memory import Contact, MeetingRecord, retain_memory, recall_memory, reset_backend

sarah = Contact("Sarah", "Product Manager", "ABC")
john = Contact("John", "CTO", "XYZ")


def flat(mem):
    return " ".join(t for v in mem.values() for t in v).lower()


def meeting1():
    return MeetingRecord(date="2026-09-01", topics=["onboarding", "pricing"],
                         preferences=["prefers data-driven decisions"],
                         promises_made=["send the analytics report"],
                         unresolved=["pricing discussion remains unresolved"])


class MemoryTests(unittest.TestCase):
    def setUp(self):
        reset_backend(None)

    def test_retain_then_recall(self):
        retain_memory(sarah, meeting1())
        mem = recall_memory(sarah)
        self.assertIn("data-driven", " ".join(mem["preferences"]).lower())
        self.assertIn("analytics report", " ".join(mem["commitments"]).lower())
        self.assertIn("pricing", " ".join(mem["unresolved"]).lower())

    def test_undelivered_promise_flagged(self):
        retain_memory(sarah, meeting1())
        self.assertTrue(any("not delivered" in t.lower() for t in recall_memory(sarah)["commitments"]))

    def test_delivered_promise_not_flagged(self):
        m = meeting1()
        m.promises_delivered = ["send the analytics report"]
        retain_memory(sarah, m)
        self.assertFalse(any("not delivered" in t.lower() for t in recall_memory(sarah)["commitments"]))

    def test_multiple_meetings_accumulate(self):
        retain_memory(sarah, meeting1())
        retain_memory(sarah, MeetingRecord(date="2026-09-15", topics=["security review"],
                                           preferences=["wants weekly email summaries"]))
        text = flat(recall_memory(sarah, top_k=20))
        for k in ("onboarding", "security review", "weekly email"):
            self.assertIn(k, text)

    def test_isolation_between_contacts(self):
        retain_memory(sarah, meeting1())
        retain_memory(john, MeetingRecord(date="2026-09-02", topics=["SOC2 audit"],
                                          preferences=["prefers phone calls"]))
        s, j = flat(recall_memory(sarah, top_k=20)), flat(recall_memory(john, top_k=20))
        self.assertNotIn("soc2", s); self.assertNotIn("phone calls", s)
        self.assertNotIn("analytics report", j); self.assertNotIn("data-driven", j)

    def test_unknown_contact_empty(self):
        self.assertEqual(flat(recall_memory(Contact("Nobody", "", "Nowhere"))), "")


if __name__ == "__main__":
    unittest.main()
