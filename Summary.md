We have attempted to enhance the MIMIC-III training data with variety in the vocabulary and introduction of new codes in synthetic data.
We applied two NER+L systems – SemEHR and MedCAT – to the training set.
We filter the NER+L outputs by intersecting them with the gold standard of MIMIC-III.
While the gold standard may not capture all mentioned concepts, it may reflect local coding guidelines.
As the NER+L systems label their outputs with CUIs, we translated these into ICD-9 using PyMedTermino.
It should be noted that LMTC models, such as CAML, rely on pre-trained word2vec features with a static vocabulary – words unseen duringpre-training will be considered out-of-vocabulary (OOV).
This affects concepts that are unseen during training, such as rare diseases named after a person – e.g., Munchausen’s Syndrome (301.51 in ICD-9). 
By introducing alternative names (augmentation) or new concepts (synthesis) we can also expand the relevant vocabulary, mitigating OOV.


## Identity-Code Augmentation
We first created a synonym-replacement DA method in order to make the models more robust to variety. 
A medical concept can have several alternative names or surface forms including abbreviations – e.g., an “acute myocardial infarction” can be referred to as “heart attack” or the abbreviation “MI”.
Through augmenting the text with synonyms we expose the model to alternative keywords representing existing concepts (already within the corpus or previously unseen), while leaving non-keyword context tokens untouched.
If an input document has any NER+L predictions matching the gold standard, their spans are identified. 
A synonym from PyMedTermino (derived from the UMLS, ICD-9, ICD-10, and SNOMED CT) is chosen at random, and replaced within the input text for each span. 
The augmented text is then added to the training set with the same gold standard labels as the original.
## Adjacent-Code Synthesis
An additional form of Document Synthesis aimed at introducing new labels, can be produced by replacing mentions of a concept with an adjacent concept, rather than a synonym – e.g., “stage 2 glaucoma” with “stage 3 glaucoma” – and updating the gold standard for the synthetic document accordingly. 
Where Identity-Code Augmentation aims to expose the model to alternative keywords to concepts pre-existing in the corpus without changing the code, the Adjacent-Code Synthesis replaces the code, exposing the model to the keyword of a different code – potentially one that is rare within the original training set, or not appearing in it at all. 
This replacement leads to these keywords appearing in new contexts (those of the concepts they replace).
We chose to focus on “unspecified” codes assuming an “unspecified” label means all its mentions
within are non-specific, while a single specified mention warrants a more specific version of the code in the new silver standard. 
This choice was made to address imperfections in the NER+L predictions – replacing a specified code would require replacement of all its mentions, some of which may not be identified by the NER+L method.
The outputs of SemEHR and MedCAT are processed as in the synonym-replacement DA. 
We considered a code to be unspecified if its description contained the string “unspecified” or “not otherwise specified”, and with with “9” as the first or “0”/“1” as the second digit of the etiology. 
Of the 8,692 unique codes appearing in the training set 1,188 remained as viable “unspecified codes”.
This represents 14.74% of the total code population within the training set.
Replacement codes were identified depending on the etiology – double-digit unspecified codes can only be replaced by codes differing only in the final digit, while single-digit unspecified codes can be replaced with codes of the same category with any other etiology. 
Replacement codes were divided into three sets – frequent (>5), few-shot (at least one but up to 5), zero-shot (unseen) – based on their population in the training set. 
Only labels known to be within the MIMIC-III dataset were considered.
For a given document each viable unspecified code is first randomly converted into a specified candidate (with ZS and FS candidates being preferred). 
The mentions of the unspecified code are randomly replaced with mentions of the specified candidate. 
The resulting synthetic discharge summary is then added into the training set with the original gold standard code replaced with the candidate code. 

