from typing import Any, List

import numpy as np
import spacy
from spacy.tokens import Doc
from spacy.training import offsets_to_biluo_tags

from dataquality.exceptions import GalileoException


def validate_obj(an_object: Any, check_type: Any, has_attr: str) -> None:
    if not isinstance(an_object, check_type):
        raise GalileoException(
            f"Expected a {check_type}. Received {str(type(an_object))}"
        )

    if not hasattr(an_object, has_attr):
        raise GalileoException(f"Your {check_type} must have a {has_attr} attribute")


def convert_spacy_ner_logits_to_valid_logits(
    logits: np.ndarray, pred: int
) -> np.ndarray:
    """Converts ParserStepModel per token logits to their matching valid logits.

    Not all logits outputted by the spacy model are valid logits, for this reason
    spacy will ignore potential actions even if they might've had the largest prob mass.
    To account for this, we first sort the logits for each token and then zero out
    all logits larger than the predicted logit (as these must've been ignored by spacy
    or else they would've become the prediction).

    :param logits: ParserStepModel logits for a single token, minus the -U tag logit
    shape of [num_classes]
    :param pred: the idx of the spacy's valid prediction from the logits
    :return: np array of logits. shape of [num_classes]
    """
    assert len(logits.shape) == 1

    # Sort in descending order
    argsorted_sample_logits = np.flip(np.argsort(logits))

    # Get all logit indices where pred_logit > logit
    # These are 'valid' because spacy ignored all logits > pred_logit
    # as it they were determined to not be possible given the current state.
    valid_logit_indices = argsorted_sample_logits[
        np.where(argsorted_sample_logits == pred)[0][0] :
    ]

    # non valid_logit_indices should be set to 0
    zero_out_mask = np.ones(logits.shape, bool)
    zero_out_mask[valid_logit_indices] = False
    logits[zero_out_mask] = 0
    return logits


def convert_spacy_ents_for_doc_to_predictions(
    docs: List[Doc], labels: List[str]
) -> List[List[int]]:
    """Converts spacy's representation of ner spans to their per token predictions.

    Uses some spacy utility code to convert from start/end/label representation to the
    BILUO per token corresponding tagging scheme.

    """
    prediction_indices = []
    for doc in docs:
        pred_output = offsets_to_biluo_tags(
            doc, [(ent.start_char, ent.end_char, ent.label_) for ent in doc.ents]
        )
        pred_output_ind = [labels.index(tok_pred) for tok_pred in pred_output]
        prediction_indices.append(pred_output_ind)
    return prediction_indices


def validate_spacy_version() -> None:
    """Validates the user is on a version of spacy we support"""
    if spacy.__version__ != "3.2.1":
        raise GalileoException(
            "Currently we only support watching SpaCy models running version 3.2.1 of "
            f"SpaCy. You have version {spacy.__version__}. Please install 3.2.1 using "
            f"the following: 'pip install --upgrade spacy==3.2.1' and then restart your"
            f"IPython kernel"
        )