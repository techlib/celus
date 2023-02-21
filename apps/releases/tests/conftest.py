import pytest


@pytest.fixture
def releases_source():
    return [
        {
            'version': '4.4.1',
            'date': '2022-05-04',
            'title': {'en': 'new release', 'cs': 'nové vydání'},
            'text': {
                'en': 'Itaque voluptas.\n### Soluta fuga\nNihil quod aliquam aut\n\n**provident '
                'quibusdam**:\n- Possimus blanditiis *repellat voluptatibus*.\n- Autem '
                'ullam [Link Text](https://example.com/) quibusdamquis et ut.',
                'cs': 'toto je nějaký text',
            },
            'is_new_feature': False,
            'is_update': False,
            'is_bug_fix': True,
            'links': [
                {'title': {'en': 'blogpost', 'cs': 'náš blog'}, 'link': 'https://example.com/'}
            ],
        },
        {
            'version': '4.4.0',
            'date': '2022-04-29',
            'title': {'en': 'even better features'},
            'text': {'en': 'Itaque quo. Nihil quod aliquam aut.'},
            'is_new_feature': True,
            'is_update': True,
            'is_bug_fix': False,
        },
        {
            'version': '4.3.3',
            'date': '2022-04-06',
            'title': {'en': 'new feature is here!', 'cs': 'nové vydání je zde!'},
            'text': {'en': 'Atque v dolore ea soluta.', 'cs': 'toto je nějaký text'},
            'is_new_feature': True,
            'is_update': False,
            'is_bug_fix': True,
            'links': [
                {'title': {'en': 'blog post', 'cs': 'náš blog'}, 'link': 'https://example.com/'},
                {'title': {'en': 'button2 title'}, 'link': 'https://example.com/'},
                {
                    'title': {'en': 'button3 title', 'cs': 'náš třetí blog'},
                    'link': 'https://example.com/',
                },
            ],
        },
    ]
