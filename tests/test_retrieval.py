from rag import store
from rag.chunker import CHUNK_CHARS, chunk_text
from rag.generate import ProgramMatch, eligibility, mark_cited, match_names

FIXTURE = [
    ("Farm Income Support", "agriculture",
     "Farm Income Support gives landholding farmer families income support of 6000 per year, "
     "paid in three equal installments. Eligible: families that own cultivable farmland. "
     "Documents required: land ownership record, identity card, bank account details."),
    ("Child Nutrition Grant", "family",
     "The Child Nutrition Grant pays a monthly allowance to mothers of children under six for food "
     "and health checkups. Documents required: child's birth certificate, mother's identity card."),
    ("Gig Worker Accident Cover", "labour",
     "Registered gig and platform workers such as delivery riders and rideshare drivers get accident "
     "insurance cover of 200000. Documents required: proof of platform work, identity card."),
]


def test_chunker_covers_text_with_overlap():
    text = " ".join(f"word{i}" for i in range(2000))
    parts = chunk_text(text)
    assert len(parts) > 1
    assert all(len(p) <= CHUNK_CHARS for p in parts)
    assert parts[1][:20] in parts[0]
    assert parts[-1].endswith("word1999")


def test_known_question_retrieves_right_program(tmp_path):
    collection = store.get_collection(tmp_path, reset=True)
    store.add(collection, [
        {"id": f"fixture_{i}", "text": text,
         "metadata": {"program_name": name, "source_file": "fixture.pdf", "page": i + 1,
                      "region": "national", "category": category}}
        for i, (name, category, text) in enumerate(FIXTURE)
    ])

    hits = store.query(collection, "I grow rice on my own small farm. Is there income support for farmers?")
    assert hits and hits[0]["metadata"]["program_name"] == "Farm Income Support"

    hits = store.query(collection, "I drive for a rideshare app, am I covered if I get hurt?")
    assert hits and hits[0]["metadata"]["program_name"] == "Gig Worker Accident Cover"

    assert store.query(collection, "best pizza toppings for a movie night") == []


def test_region_filter_keeps_other_regions_out(tmp_path):
    collection = store.get_collection(tmp_path, reset=True)
    store.add(collection, [
        {"id": f"r{i}", "text": FIXTURE[0][2],
         "metadata": {"program_name": f"Farm Income Support {region}", "source_file": f"{region}.pdf", "page": 1,
                      "region": region, "category": "agriculture"}}
        for i, region in enumerate(["North", "South"])
    ])
    assert store.regions(collection) == ["North", "South"]
    hits = store.query_many(collection, ["income support for my small farm"], region="South")
    assert [h["metadata"]["region"] for h in hits] == ["South"]



def test_each_need_in_a_situation_gets_searched(tmp_path):
    from app import situation_parts
    from evals.run_eval import corpus_chunks

    collection = store.get_collection(tmp_path, reset=True)
    store.add(collection, corpus_chunks())
    question = "24 year old rideshare driver, married, one kid aged 3"
    found = {c["metadata"]["program_name"] for c in store.query_many(collection, [question, *situation_parts(question)])}
    assert {"Gig Worker Accident Cover", "Child Nutrition Grant"} <= found


def test_citation_must_point_at_a_retrieved_page():
    chunks = [{"text": "...", "metadata": {"source_file": "farm.pdf", "page": 2}}]
    base = dict(program_name="Farm Income Support",
                who_its_for={"group": "farmers", "household_member": "the person", "persons_fact": "farmer",
                             "member_is_in_group": "yes"},
                who_can_apply=[{"requirement": "owns up to 5 acres", "persons_fact": "owns 3 acres", "person_fits": "yes"}],
                who_cannot_apply=[],
                benefit="6000 per year", why_you_match="owns farmland",
                documents_required=["land record"])
    real = ProgramMatch(**base, source_file="farm.pdf", page=2)
    wrong_page = ProgramMatch(**base, source_file="farm.pdf", page=9)
    invented = ProgramMatch(**base, source_file="made-up.pdf", page=2)
    assert [p["cited"] for p in mark_cited([real, wrong_page, invented], chunks)] == [True, False, False]


def test_eligibility_is_decided_by_rule_checks():
    def program(target="yes", fits=(), excluded=()):
        return ProgramMatch(program_name="X", benefit="", why_you_match="", documents_required=[], source_file="x", page=1,
                            who_its_for={"group": "g", "household_member": "m", "persons_fact": "f",
                                         "member_is_in_group": target},
                            who_can_apply=[{"requirement": "r", "persons_fact": "f", "person_fits": s} for s in fits],
                            who_cannot_apply=[{"group": "g", "persons_fact": "f", "person_is_in_group": s}
                                              for s in excluded])
    assert eligibility(program("yes", ["yes", "yes"], ["no"])) == "meets_all_rules"
    assert eligibility(program("yes")) == "meets_all_rules"
    assert eligibility(program("yes", ["yes", "unknown"])) == "some_facts_unknown"
    assert eligibility(program("yes", ["unknown", "unknown"])) == "some_facts_unknown"
    assert eligibility(program("yes", ["yes"], ["unknown"])) == "some_facts_unknown"
    assert eligibility(program("yes", ["yes", "no"])) == "not_eligible"
    assert eligibility(program("yes", ["yes"], ["yes"])) == "not_eligible"
    assert eligibility(program("unknown", ["yes"])) == "not_eligible"
    assert eligibility(program("no", ["yes"])) == "not_eligible"
    assert eligibility(program("unknown", [], ["no", "no"])) == "not_eligible"


def test_program_names_match_what_was_retrieved():
    chunks = [{"text": "...", "metadata": {"program_name": n, "source_file": "f.pdf", "page": 1}}
              for n in ["WIC", "Earned Income Credit", "Pension Credit"]]

    def named(name):
        return ProgramMatch(program_name=name, benefit="", why_you_match="", documents_required=[], source_file="f.pdf",
                            page=1, who_can_apply=[], who_cannot_apply=[],
                            who_its_for={"group": "g", "household_member": "m", "persons_fact": "f",
                                         "member_is_in_group": "yes"})

    said = ["WIC Program", "Earned Income Credit (EIC)", "wic", "Pension Credt", "Free Bus Pass"]
    assert [p.program_name for p in match_names([named(n) for n in said], chunks)] == \
        ["WIC", "Earned Income Credit", "Pension Credit"]
