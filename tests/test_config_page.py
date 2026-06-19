from PySide6.QtWidgets import QFrame, QLabel, QScrollArea, QWidget

from llama_app.ui.widgets.config_page import (
    DefaultFloatField,
    DefaultIntField,
    SectionTitle,
    make_scroll_page,
)


def test_make_scroll_page_is_resizable_and_frameless(qtbot):
    content = QWidget()
    scroll = make_scroll_page(content)
    qtbot.addWidget(scroll)

    assert isinstance(scroll, QScrollArea)
    assert scroll.widget() is content
    assert scroll.widgetResizable()
    assert scroll.frameShape() == QFrame.NoFrame


def test_section_title_contains_title_and_description(qtbot):
    title = SectionTitle("模型", "选择模型文件")
    qtbot.addWidget(title)

    assert isinstance(title, QLabel)
    assert title.objectName() == "sectionTitle"
    assert "模型" in title.text()
    assert "选择模型文件" in title.text()


def test_default_int_field_distinguishes_none_and_zero(qtbot):
    field = DefaultIntField(0, 100, "自动")
    qtbot.addWidget(field)

    assert field.config_value() is None
    assert "使用 llama 默认值（自动）" == field.use_default.text()
    field.set_config_value(0)
    assert field.config_value() == 0
    assert field.spin.isEnabled()
    field.set_config_value(None)
    assert field.config_value() is None


def test_default_float_field_round_trips_none_and_explicit_zero(qtbot):
    field = DefaultFloatField(0.0, 1.0, 0.01, "0.8")
    qtbot.addWidget(field)

    assert field.config_value() is None
    field.set_config_value(0.0)
    assert field.config_value() == 0.0
    field.set_config_value(None)
    assert field.config_value() is None


def test_setting_same_config_value_does_not_emit_changed(qtbot):
    field = DefaultIntField(0, 100, "自动")
    qtbot.addWidget(field)
    emissions = []
    field.changed.connect(lambda: emissions.append(True))

    field.set_config_value(None)
    assert emissions == []

    field.set_config_value(0)
    emissions.clear()
    field.set_config_value(0)
    assert emissions == []
