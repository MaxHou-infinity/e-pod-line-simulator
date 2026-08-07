"""术语库单元测试"""

from src.glossary import GLOSSARY, glossary_text


def test_glossary_has_key_terms():
    terms = {term for term, _ in GLOSSARY}
    for required in ["工序", "并联", "协同", "OEE", "WIP", "瓶颈", "UPPH", "日成本", "日产量"]:
        assert required in terms


def test_glossary_text_output():
    text = glossary_text()
    assert "WIP：在制品" in text
    assert "日成本：总人数 × 时薪 × 班次时长（元/天）。" in text


def test_glossary_dialog_class_available():
    from src.gui_panels import GlossaryDialog
    assert callable(GlossaryDialog)
