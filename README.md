# Ontology-guided Augmentation and Synthesis for ICD-9 Coding.

Addressing concept sparsity -- either due to surface-form variety (synonymy) or concept absence in the training data -- in ICD-9 coding with the aid of medical ontologies. Designed to work with the discharge summaries in the MIMIC-III dataset.

## Library Requirements

### Essential

``numpy``
``pandas``
``owlready2``

### Non-essential

``tqdm``

## External Resources
``ICD-9 graph`` as seen in the CoPHE repository
``MedCAT``
``MIMIC-III`` or a similar corpus with ICD-9 labels
``SemEHR``
``UMLS``

## Scripts

``string_manipulation.py``
This script cotains the augment method for creating strings through replacing stated substrings on specified positions with alternatives.

``synonym_setup.py``
Sets up the synonym conversion table for data augmentation given a dataset and its corresponding NER output.

``adjacent_setup.py``
Sets up the conversion table for adjacent concepts for data synthesis (specifying the unspecified).

``augmentation_and_sythesis.py``
Runs the actual augmentation and synthesis routines given a dataset and conversion tables.

## Use
First prepare your data (e.g., MIMIC-III), your UMLS distirbution, and your NER engine (e.g., SemEHR, or MedCAT).

Run synonym\_setup.py the using raw labelled data in CSV format (path goes to disch-csv\_path) and the output of your NER engine. A sample list of entities in the accepted format is presented in sample\_entities.csv (these were derived from a freely accessible discharge summary in MT Samples). This script produces a synonym dictionary (syns.csv) and a CSV that combines the NER output with the synonyms (ner\_output\_with\_syns.csv). This should have you set for augmentation.

Run adjacent\_setup.py with specitying the path to your dataset and the path to the ICD-9 graph. This will create a conversion table between the assign codes and their siblings/cousins.

Run augmentation\_and\_synthesis.py, this actually performs the augmentation and synthesis. Sections of code related to each of these is indicated via comments and printouts, if you wish to only do one of these, just remove/comment them out of the main function. Note that the augmentation and sythesis involve some randomness in picking replacements, hence to make your augmentation/synthesis reproducible please use a random seed (this is currently set to 50). Furthermore, there is some value in running augmentation/synthesis multiple times and then de-duplicating the result as multiple synonyms/related codes may be used for replacement in the same situation. This behaviour is already implemented in the case of run\_synthesis\_adj with the iters parameter.

## Theoretical background

For a theoretical background behind this implementation, please refer to the [Horses to Zebras paper](https://aclanthology.org/2022.bionlp-1.39/).
An informal summary can be found in ``Summary.md``.
