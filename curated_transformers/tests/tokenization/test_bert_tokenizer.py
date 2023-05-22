import pytest
import torch

from curated_transformers._compat import has_hf_transformers
from curated_transformers.tokenization import PiecesWithIds
from curated_transformers.tokenization import BertTokenizer
from curated_transformers.tokenization.bert_tokenizer import BertPreEncoder

from ..util import torch_assertclose, compare_tokenizer_outputs_with_hf_tokenizer


@pytest.fixture
def toy_tokenizer(test_dir):
    return BertTokenizer.from_files(
        vocab_path=test_dir / "toy.wordpieces",
    )


@pytest.mark.skipif(not has_hf_transformers, reason="requires huggingface transformers")
@pytest.mark.slow
def test_berttokenizer_hf_tokenizer(sample_texts):
    compare_tokenizer_outputs_with_hf_tokenizer(
        sample_texts, "bert-base-cased", BertTokenizer
    )


def test_bert_toy_tokenizer(toy_tokenizer, short_sample_texts):
    encoding = toy_tokenizer(short_sample_texts)
    _check_toy_tokenizer(encoding)

    assert toy_tokenizer.decode(encoding.ids) == [
        "I saw a girl with a telescope.",
        "Today we will eat pok [UNK] bowl, lots of it!",
    ]


def _check_toy_tokenizer(pieces):
    assert isinstance(pieces, PiecesWithIds)
    assert len(pieces.ids) == 2
    assert len(pieces.pieces) == 2

    assert pieces.lens == [
        [1, 1, 1, 1, 3, 1, 1, 5, 1, 1],
        [1, 3, 1, 1, 2, 3, 3, 1, 3, 1, 1, 1, 1],
    ]
    assert pieces.ids == [
        [2, 41, 818, 61, 67, 193, 88, 204, 61, 251, 909, 682, 102, 95, 17, 3],
        [
            2,
            824,
            98,
            189,
            311,
            417,
            65,
            155,
            503,
            99,
            1,
            416,
            117,
            88,
            15,
            844,
            91,
            100,
            163,
            183,
            5,
            3,
        ],
    ]
    assert pieces.pieces == [
        [
            "[CLS]",
            "I",
            "saw",
            "a",
            "g",
            "##ir",
            "##l",
            "with",
            "a",
            "te",
            "##les",
            "##co",
            "##p",
            "##e",
            ".",
            "[SEP]",
        ],
        [
            "[CLS]",
            "To",
            "##d",
            "##ay",
            "we",
            "will",
            "e",
            "##at",
            "po",
            "##k",
            "[UNK]",
            "bo",
            "##w",
            "##l",
            ",",
            "lo",
            "##t",
            "##s",
            "of",
            "it",
            "!",
            "[SEP]",
        ],
    ]

    torch_assertclose(
        pieces.padded_tensor(padding_id=1),
        torch.tensor(
            [
                [
                    2,
                    41,
                    818,
                    61,
                    67,
                    193,
                    88,
                    204,
                    61,
                    251,
                    909,
                    682,
                    102,
                    95,
                    17,
                    3,
                    1,
                    1,
                    1,
                    1,
                    1,
                    1,
                ],
                [
                    2,
                    824,
                    98,
                    189,
                    311,
                    417,
                    65,
                    155,
                    503,
                    99,
                    1,
                    416,
                    117,
                    88,
                    15,
                    844,
                    91,
                    100,
                    163,
                    183,
                    5,
                    3,
                ],
            ],
            dtype=torch.int32,
        ),
    )
    torch_assertclose(
        pieces.attention_mask,
        torch.tensor(
            [
                [
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                ],
                [
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                    True,
                ],
            ]
        ),
    )


def test_bert_tokenizer_preencoder():
    preencoder = BertPreEncoder(lowercase=False, strip_accents=True)
    assert preencoder(["AWO-Mitarbeiter"]) == ["AWO - Mitarbeiter"]
    assert preencoder(["-Mitarbeiter"]) == ["- Mitarbeiter"]
    assert preencoder(["AWO-"]) == ["AWO -"]
    assert preencoder(["-"]) == ["-"]
    assert preencoder([""]) == [""]
    assert preencoder(["Brötchen"]) == ["Brotchen"]
    assert preencoder(["Mw.-St."]) == ["Mw . - St ."]
