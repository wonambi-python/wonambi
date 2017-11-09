from plotly.offline import plot

from .paths import PLOTLY_PATH


def save_plotly_fig(fig, name):
    div = plot(fig, include_plotlyjs=False, output_type='div', show_link=False)
    with (PLOTLY_PATH / (name + '.html')).open('w') as f:
        f.write(div)
