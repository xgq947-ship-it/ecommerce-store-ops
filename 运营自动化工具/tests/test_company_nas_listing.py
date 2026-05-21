from pathlib import Path

from tasks.company_nas_listing import selected_files


def touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"image")


def test_selected_files_keeps_detail_790_layouts(tmp_path: Path) -> None:
    product = tmp_path / "703"
    touch(product / "主图" / "主图" / "a_800.jpg")
    touch(product / "sku" / "sku_800.jpeg")
    touch(product / "详情切片" / "790" / "detail_a.jpg")
    touch(product / "详情切片" / "x_790.gif")
    touch(product / "详情切片" / "750" / "detail_b.jpg")
    touch(product / "场景图" / "scene_800.jpg")
    touch(product / "白底透明" / "white_800.png")

    rel_paths = {p.relative_to(product) for p in selected_files(product, include_buyer_show=False)}

    assert Path("主图/主图/a_800.jpg") in rel_paths
    assert Path("sku/sku_800.jpeg") in rel_paths
    assert Path("详情切片/790/detail_a.jpg") in rel_paths
    assert Path("详情切片/x_790.gif") in rel_paths
    assert Path("详情切片/750/detail_b.jpg") not in rel_paths
    assert Path("场景图/scene_800.jpg") in rel_paths
    assert Path("白底透明/white_800.png") in rel_paths
