---

language: 
  - en
tags:
- coreference-resolution
- maverick
- efficient
- accurate
license:   
- cc-by-nc-sa-4.0
datasets:
- OntoNotes
metrics:
- CoNLL
task_categories:
- coreference-resolution
model-index:
- name: sapienzanlp/maverick-mes-ontonotes
  results:
  - task:
      type: coreference-resolution
      name: coreference-resolution
    dataset:
      name: ontonotes
      type: coreference
    metrics:
    - name: Avg. F1
      type: CoNLL
      value: 83.6

---
# Maverick mes OntoNotes
Official weights for *Maverick-mes* trained on OntoNotes and based on DeBERTa-large.
This model achieves 83.6 Avg CoNLL-F1 on OntoNotes.

Other available models at [SapienzaNLP huggingface hub](https://huggingface.co/collections/sapienzanlp/maverick-coreference-resolution-66a750a50246fad8d9c7086a):

|            hf_model_name            | training dataset | Score | Singletons |
|:-----------------------------------:|:----------------:|:-----:|:----------:|
|    ["sapienzanlp/maverick-mes-ontonotes"](https://huggingface.co/sapienzanlp/maverick-mes-ontonotes)    |     OntoNotes    |  83.6 |     No     |
|     ["sapienzanlp/maverick-mes-litbank"](https://huggingface.co/sapienzanlp/maverick-mes-litbank)     |      LitBank     |  78.0 |     Yes    |
|      ["sapienzanlp/maverick-mes-preco"](https://huggingface.co/sapienzanlp/maverick-mes-preco)      |       PreCo      |  87.4 |     Yes    |
<!-- |    ["sapienzanlp/maverick-s2e-ontonotes"](https://huggingface.co/sapienzanlp/maverick-mes-preco)    |     OntoNotes    |  83.4 |     No     |     No    | -->
<!-- |    "sapienzanlp/maverick-incr-ontonotes"   |     Ontonotes    |  83.5 |     No     |     No    | -->
<!-- |  "sapienzanlp/maverick-mes-ontonotes-base" |     Ontonotes    |  81.4 |     No     |     No    | -->
<!-- | "sapienzanlp/maverick-s2e-ontonotes-base"  |     Ontonotes    |  81.1 |     No     |     No    | -->
<!-- | "sapienzanlp/maverick-incr-ontonotes-base" |     Ontonotes    |  81.0 |     No     |     No    | -->
<!-- |     "sapienzanlp/maverick-s2e-litbank"     |      LitBank     |  77.6 |     Yes    |     No    | -->
<!-- |     "sapienzanlp/maverick-incr-litbank"    |      LitBank     |  78.3 |     Yes    |     No    | -->
<!-- |      "sapienzanlp/maverick-s2e-preco"      |       PreCo      |  87.2 |     Yes    |     No    | -->
<!-- |      "sapienzanlp/maverick-incr-preco"     |       PreCo      |  88.0 |     Yes    |     No    | -->
N.B. Each dataset has different annotation guidelines, choose your model according to your use case.

### Results on OntoNotes
<img src="https://cdn-uploads.huggingface.co/production/uploads/65e9ccd84ce78d665a50f78b/-5Wi_xL2o-71uQcl3d8B9.png" alt="drawing" width="95%"/>

## Maverick: Efficient and Accurate Coreference Resolution Defying recent trends

[![Conference](https://img.shields.io/badge/ACL%202024%20Paper-red)](https://arxiv.org/pdf/2407.21489)
[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-green.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
[![Pip Package](https://img.shields.io/badge/🐍%20Python%20package-blue)](https://pypi.org/project/maverick-coref/)
[![git](https://img.shields.io/badge/Git%20Repo%20-yellow.svg)](https://github.com/SapienzaNLP/maverick-coref)

### Citation

```
@inproceedings{martinelli-etal-2024-maverick,
    title = "Maverick: Efficient and Accurate Coreference Resolution Defying Recent Trends",
    author = "Martinelli, Giuliano and
      Barba, Edoardo  and
      Navigli, Roberto",
        booktitle = "Proceedings of the Annual Meeting of the Association for Computational Linguistics (ACL 2024)",
    year      = "2024",
    address   = "Bangkok, Thailand",
    publisher = "Association for Computational Linguistics",
}
```