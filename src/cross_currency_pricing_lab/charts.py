from __future__ import annotations

from pathlib import Path


def write_grouped_bar_chart_svg(
    *,
    title: str,
    categories: list[str],
    left_values: list[float],
    right_values: list[float | None],
    left_label: str,
    right_label: str,
    output_path: Path,
) -> None:
    width = 1500
    height = 920
    chart_left = 150
    chart_bottom = 780
    chart_top = 180
    chart_width = 1200
    chart_height = chart_bottom - chart_top
    maximum = max(
        max(left_values) if left_values else 0.0,
        max(value for value in right_values if value is not None) if any(value is not None for value in right_values) else 0.0,
    )
    maximum = maximum * 1.15 if maximum > 0.0 else 1.0
    category_width = chart_width / max(len(categories), 1)

    svg_lines = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg">',
        '<rect width="1500" height="920" rx="28" fill="#0B1220"/>',
        f'<text x="{chart_left}" y="110" fill="#F5F7FB" font-size="40" font-weight="700" font-family="SF Pro Display, Helvetica, Arial, sans-serif">{title}</text>',
        f'<text x="{chart_left}" y="146" fill="#91A4BD" font-size="18" font-family="SF Pro Text, Helvetica, Arial, sans-serif">Analytic prices are shown where available; Monte Carlo prices use the same base scenario.</text>',
        '<line x1="150" y1="780" x2="1350" y2="780" stroke="#32455E" stroke-width="2"/>',
        '<line x1="150" y1="180" x2="150" y2="780" stroke="#32455E" stroke-width="2"/>',
        '<rect x="1050" y="84" width="18" height="18" rx="4" fill="#58D0FF"/>',
        f'<text x="1082" y="99" fill="#DDE8F4" font-size="16" font-family="SF Pro Text, Helvetica, Arial, sans-serif">{left_label}</text>',
        '<rect x="1240" y="84" width="18" height="18" rx="4" fill="#7DF0C4"/>',
        f'<text x="1272" y="99" fill="#DDE8F4" font-size="16" font-family="SF Pro Text, Helvetica, Arial, sans-serif">{right_label}</text>',
    ]

    for grid_index in range(5):
        y = chart_bottom - chart_height * grid_index / 4
        value = maximum * grid_index / 4
        svg_lines.append(f'<line x1="{chart_left}" y1="{y:.1f}" x2="1350" y2="{y:.1f}" stroke="#1B2B40" stroke-width="1"/>')
        svg_lines.append(
            f'<text x="70" y="{y + 6:.1f}" fill="#7890AA" font-size="16" font-family="SF Pro Text, Helvetica, Arial, sans-serif">{value:.2f}</text>'
        )

    for index, category in enumerate(categories):
        center = chart_left + category_width * (index + 0.5)
        bar_width = min(90.0, category_width * 0.28)
        left_height = chart_height * left_values[index] / maximum
        left_x = center - bar_width - 8
        left_y = chart_bottom - left_height
        svg_lines.append(
            f'<rect x="{left_x:.1f}" y="{left_y:.1f}" width="{bar_width:.1f}" height="{left_height:.1f}" rx="14" fill="#58D0FF"/>'
        )
        svg_lines.append(
            f'<text x="{left_x - 8:.1f}" y="{left_y - 10:.1f}" fill="#CFE7FA" font-size="14" font-family="SF Pro Text, Helvetica, Arial, sans-serif">{left_values[index]:.3f}</text>'
        )

        if right_values[index] is not None:
            right_height = chart_height * right_values[index] / maximum
            right_x = center + 8
            right_y = chart_bottom - right_height
            svg_lines.append(
                f'<rect x="{right_x:.1f}" y="{right_y:.1f}" width="{bar_width:.1f}" height="{right_height:.1f}" rx="14" fill="#7DF0C4"/>'
            )
            svg_lines.append(
                f'<text x="{right_x - 8:.1f}" y="{right_y - 10:.1f}" fill="#D7F9EA" font-size="14" font-family="SF Pro Text, Helvetica, Arial, sans-serif">{right_values[index]:.3f}</text>'
            )

        svg_lines.append(
            f'<text x="{center - category_width * 0.3:.1f}" y="832" fill="#AABED6" font-size="15" font-family="SF Pro Text, Helvetica, Arial, sans-serif">{category}</text>'
        )

    svg_lines.append("</svg>")
    output_path.write_text("\n".join(svg_lines), encoding="utf-8")


def write_dual_line_chart_svg(
    *,
    title: str,
    subtitle: str,
    x_values: list[float],
    left_values: list[float],
    right_values: list[float],
    output_path: Path,
) -> None:
    width = 1500
    height = 920
    chart_left = 140
    chart_right = 1350
    chart_top = 200
    chart_bottom = 780
    chart_width = chart_right - chart_left
    chart_height = chart_bottom - chart_top
    x_min = min(x_values)
    x_max = max(x_values)
    y_min = min(min(left_values), min(right_values))
    y_max = max(max(left_values), max(right_values))
    y_span = max(y_max - y_min, 1.0e-8)
    y_min -= 0.08 * y_span
    y_max += 0.10 * y_span
    y_span = y_max - y_min

    def project_x(value: float) -> float:
        return chart_left + (value - x_min) / (x_max - x_min) * chart_width

    def project_y(value: float) -> float:
        return chart_bottom - (value - y_min) / y_span * chart_height

    analytic_path = " ".join(
        ("M" if index == 0 else "L") + f" {project_x(x_value):.2f} {project_y(value):.2f}"
        for index, (x_value, value) in enumerate(zip(x_values, left_values))
    )
    mc_path = " ".join(
        ("M" if index == 0 else "L") + f" {project_x(x_value):.2f} {project_y(value):.2f}"
        for index, (x_value, value) in enumerate(zip(x_values, right_values))
    )

    svg_lines = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg">',
        '<rect width="1500" height="920" rx="28" fill="#0B1220"/>',
        f'<text x="{chart_left}" y="108" fill="#F5F7FB" font-size="40" font-weight="700" font-family="SF Pro Display, Helvetica, Arial, sans-serif">{title}</text>',
        f'<text x="{chart_left}" y="146" fill="#91A4BD" font-size="18" font-family="SF Pro Text, Helvetica, Arial, sans-serif">{subtitle}</text>',
        f'<line x1="{chart_left}" y1="{chart_bottom}" x2="{chart_right}" y2="{chart_bottom}" stroke="#32455E" stroke-width="2"/>',
        f'<line x1="{chart_left}" y1="{chart_top}" x2="{chart_left}" y2="{chart_bottom}" stroke="#32455E" stroke-width="2"/>',
        '<rect x="1020" y="84" width="18" height="18" rx="4" fill="#FFC86E"/>',
        '<text x="1052" y="99" fill="#DDE8F4" font-size="16" font-family="SF Pro Text, Helvetica, Arial, sans-serif">Analytic</text>',
        '<rect x="1170" y="84" width="18" height="18" rx="4" fill="#61D9FF"/>',
        '<text x="1202" y="99" fill="#DDE8F4" font-size="16" font-family="SF Pro Text, Helvetica, Arial, sans-serif">Monte Carlo</text>',
    ]

    for grid_index in range(5):
        y = chart_bottom - chart_height * grid_index / 4
        value = y_min + y_span * grid_index / 4
        svg_lines.append(f'<line x1="{chart_left}" y1="{y:.1f}" x2="{chart_right}" y2="{y:.1f}" stroke="#1B2B40" stroke-width="1"/>')
        svg_lines.append(
            f'<text x="42" y="{y + 6:.1f}" fill="#7890AA" font-size="16" font-family="SF Pro Text, Helvetica, Arial, sans-serif">{value:.4f}</text>'
        )

    for x_value in x_values:
        x = project_x(x_value)
        svg_lines.append(f'<line x1="{x:.1f}" y1="{chart_top}" x2="{x:.1f}" y2="{chart_bottom}" stroke="#132338" stroke-width="1"/>')
        svg_lines.append(
            f'<text x="{x - 18:.1f}" y="820" fill="#AABED6" font-size="15" font-family="SF Pro Text, Helvetica, Arial, sans-serif">{x_value:+.2f}</text>'
        )

    svg_lines.append(f'<path d="{analytic_path}" stroke="#FFC86E" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>')
    svg_lines.append(f'<path d="{mc_path}" stroke="#61D9FF" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>')

    for x_value, value in zip(x_values, left_values):
        svg_lines.append(f'<circle cx="{project_x(x_value):.2f}" cy="{project_y(value):.2f}" r="7" fill="#FFC86E"/>')
    for x_value, value in zip(x_values, right_values):
        svg_lines.append(f'<circle cx="{project_x(x_value):.2f}" cy="{project_y(value):.2f}" r="7" fill="#61D9FF"/>')

    svg_lines.append("</svg>")
    output_path.write_text("\n".join(svg_lines), encoding="utf-8")
