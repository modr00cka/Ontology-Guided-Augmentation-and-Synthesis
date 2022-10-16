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


def filter_code(icd9s:list)->str:
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
    
def convert_cui_to_icd9(cui:str)->list:
    """
    Converts a CUI to ICD9
    """
    cui_concept = CUI[cui]
    if cui_concept:
        icd9s = cui_concept >> ICD9CM # the ">>" operator signifies translation -- here a CUI is converted into ICD9(s)
        return filter_code(icd9s)
    else:
        return None
        
def filter_unspecifieds(syns:list)->list:
    """
    Filters code names/synonyms that include the obsolete ``unspecified'' token. Also removes names involving phrases in paretheses, favouring versions where the concept name is stated without them.
    Example: keep ``primary hypertension'', remove ``unspecified primary hypertension'', remove ``hypertension (primary)''
    """
    filtered_syns =[]
    unspecifieds = []
    
    # Keep specified code descriptions/synonyms
    for syn in syns:
        lower_syn = syn.lower()
        if "(unspecified)" not in lower_syn and 'unspecified' not in lower_syn and "not otherwise specified" not in lower_syn and "(" not in lower_syn:
            filtered_syns.append(syn)
        else:
            unspecifieds.append(syn)
            
    # if no specified descriptions/synonyms are available for a code, try to build it by removing '(unspecified)' or 'not otherwise specified'
    if filtered_syns == []:
        for unspecified in unspecifieds:
            lower_syn = syn.lower()
            for phrase in ['(unspecified)', 'not otherwise specified']:
               if phrase in lower_syn:
                    fixed = ' '.join(lower_syn.split(phrase))
                    filtered_syns.append(fixed)
    	
    return filtered_syns

def set_up_synonyms_CUI(cui:str, drop_unspecified:bool = True)->str:
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
        
def set_up_synonyms_ICD9(icd9:str, drop_unspecified:bool = True)->list:
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

def syndf_setup(data_df:pd.core.frame.DataFrame)->pd.core.frame.DataFrame:
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
    
def convert_code_and_populate_syns_cui(result_df:pd.core.frame.DataFrame)->pd.core.frame.DataFrame:
    """
    Provides conversion to ICD9 from CUI and creation of synonyms -- this is useful when applying to the output of the NER+L engine, which should retrun CUIs (e.g., SemEHR/MedCAT)
    """
    output_df = result_df.copy()
    output_df["ICD9"] = result_df["CUI"].apply(convert_cui_to_icd9)
    output_df["synonyms"] = output_df["CUI"].apply(set_up_synonyms_CUI)
    return output_df
        
if __name__ == "__main__":
    disch_csv_path = "/path/to/raw/MIMIC/discharge/summaries.csv"
    ner_output_path = "/path/to/ner/output.csv"
    ner_output_df = pd.read_csv(ner_output_path)
    ner_output_df_with_syns = convert_code_and_populate_syns_cui(ner_output_df)
    data = pd.read_csv(disch_csv_path)
    syns = (syndf_setup(data))
    syns.to_csv("syns.csv")
    ner_output_df_with_syns.to_csv('ner_output_with_syns.csv')
