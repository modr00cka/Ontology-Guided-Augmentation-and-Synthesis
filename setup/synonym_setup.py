from owlready2 import *
from owlready2.pymedtermino2 import *
from owlready2.pymedtermino2.umls import *
import pandas as pd


# load up UMLS, create a pymedtermino world, populate it with desired ontologies (here ICD9CM, ICD10, SNOMEDCT_US, CUT)
umls_path = "path/to/umls/folder/" 
default_world.set_backend(filename = "pym.sqlite3")
import_umls(umls_path+"umls-2021AA-full.zip", terminologies = ["ICD9CM","ICD10", "SNOMEDCT_US","CUI"])
default_world.save()

# Populate ontological variables
PYM = get_ontology("http://PYM/").load()
CUI = PYM["CUI"]
ICD9CM = PYM["ICD9CM"]
SNOMED = PYM["SNOMEDCT_US"]
ICD10 = PYM["ICD10"]


def filter_code(icd9s):
    """
    Filter function aimed at removing less specific versions of a code (parents/grandparents) if returned as part of the transaltion from UMLS.
    Only the longest (most specific) code is kept.
    """
    max_len = 0
    max_len_code = None
    for icd9 in icd9s:
        if max_len<len(icd9.name):
            max_len = len(icd9.name)
            max_len_code = icd9.name
    return(max_len_code)
    
def convert_cui_to_icd9(cui):
    """
    Converts a CUI to ICD9
    """
    cui_concept = CUI[cui]
    if cui_concept:
        icd9s = cui_concept >> ICD9CM # the ">>" operator signifies translation -- here a CUI is converted into ICD9(s)
        return filter_code(icd9s)
    else:
        return None
        
def filter_unspecifieds(syns):
    """
    Filters code names/synonyms that include the obsolete ``unspecified'' token. Also removes names involving phrases in paretheses, favouring versions where the concept name is stated without them.
    Example: keep ``primary hypertension'', remove ``unspecified primary hypertension'', remove ``hypertension (primary)''
    """
    filtered_syns =[]
    for syn in syns:
        if "unspecified" not in syn.lower() and "(" not in syn.lower():
            filtered_syns.append(syn)
    return filtered_syns

def set_up_synonyms_CUI(cui, drop_unspecified = True):
    """
    Given a CUI, provides a list of synonyms of the concept. Allows filtering synonyms following patterns common for ``unspecified''
    The list of synonyms is return of a string consisting of the list elements joined by ``|'' characters.
    """
    cui_concept = CUI[cui]
    if cui_concept:
        syns = cui_concept.synonyms + cui_concept.label
        syns = set(syns)
        if drop_unspecified:
            syns = filter_unspecifieds(syns)
        syns = set(syns)
        return '|'.join(syns)
    else:
        return None
        
def set_up_synonyms_ICD9(icd9, drop_unspecified = True):
    """
    Given an ICD9CM code first checks if it can be converted to CUI and back to ICD9. If false, do not produce synonyms. If conversion is successful, use the CUI concepts to find synonyms using the set_up_synonyms_CUI method. 
    """
    syn_result = []
    icd9concept = (ICD9CM[icd9])
    if not(icd9concept):
        return None
    cui_concepts = ICD9CM[icd9] >> CUI
    icd9s = cui_concepts >> ICD9CM
    icd9_names = [i.name for i in icd9s]
    if icd9 not in icd9_names:
        return None

    syn_string = ""
    for concept in cui_concepts:
        res = set_up_synonyms_CUI(concept.name, drop_unspecified)
        if res is not None:
            syn_result.append((concept.name, res))
    return syn_result

def syndf_setup(data_df):
    """
    Creates a conversion table for your data in order to streamline the lookup process (avoiding unnecessary future loading of the UMLS/pymedtermino)
    Considers labels within the dataframe representing your dataset (e.g., MIMIC-III), creates synonym lists for the existing labels, returns them as a dataframe.
    """
    gold_label_set = set()
    label_lists = list(data_df.LABELS)
    for label_list in label_lists:
        gold_label_set = gold_label_set.union(set(str(label_list).split(";")))
    gold_label_list = list(gold_label_set)
    syn_list = []
    viable_labels = []
    for gold_label in gold_label_list:
        syns = set_up_synonyms_ICD9(gold_label, True)
        if syns:
            syn_list.append(syns[0][1])
            viable_labels.append(gold_label)
    icd9syn_df = pd.DataFrame({"LABEL":viable_labels, "SYNONYMS":syn_list})
    return icd9syn_df 
    
def convert_code_and_populate_syns_cui(result_df):
    """
    Provides conversion to ICD9 from CUI and creation of synonyms -- this is useful when applying to the output of the NER+L engine, which should retrun CUIs (e.g., SemEHR/MedCAT)
    """
    output_df = result_df.copy()
    output_df["ICD9"] = result_df["CUI"].apply(convert_cui_to_icd9)
    output_df["synonyms"] = output_df["CUI"].apply(set_up_synonyms_CUI)
    return result_df
        
if __name__ == "__main__":
    
    data = pd.read_csv("/path/to/MIMIC/discharge/summaries.csv")
    syns = (syndf_setup(enriched_raw))
    syns.to_csv("syns.csv")
