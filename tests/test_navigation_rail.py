from PySide6.QtCore import Qt

from llama_app.ui.widgets.navigation_rail import NavigationRail


def test_navigation_rail_selects_first_page_by_default(qtbot):
    rail = NavigationRail()
    qtbot.addWidget(rail)

    assert rail.objectName() == "navigationRail"
    assert rail.current_page() == "model"


def test_navigation_rail_emits_selected_page_key(qtbot):
    rail = NavigationRail()
    qtbot.addWidget(rail)

    with qtbot.waitSignal(rail.page_selected) as blocker:
        rail.select_page("network")

    assert blocker.args == ["network"]
    assert rail.current_page() == "network"


def test_navigation_items_keep_stable_keys(qtbot):
    rail = NavigationRail()
    qtbot.addWidget(rail)

    keys = [rail.page_list.item(row).data(Qt.UserRole) for row in range(rail.page_list.count())]
    assert keys == ["model", "performance", "network", "sampling", "advanced", "monitor", "presets"]
    assert rail.page_list.focusPolicy() != Qt.NoFocus


def test_navigation_items_wrap_without_horizontal_scrolling(qtbot):
    rail = NavigationRail()
    qtbot.addWidget(rail)

    assert rail.page_list.wordWrap()
    assert rail.page_list.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff


def test_navigation_rail_updates_resources_and_unavailable_values(qtbot):
    rail = NavigationRail()
    qtbot.addWidget(rail)

    rail.update_resources(cpu=12, ram_gb=5.2, vram_gb=None, gpu=None)

    assert "12%" in rail.resource_text("cpu")
    assert "5.2 GB" in rail.resource_text("ram")
    assert "N/A" in rail.resource_text("vram")
    assert "N/A" in rail.resource_text("gpu")

