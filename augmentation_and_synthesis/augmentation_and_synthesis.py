from random import choice, seed
import pandas as pd

from string_manipulation import augment
import random
import re
import logging
from tqdm import tqdm

logging.addLevelName(25, "AUGMENTS")

logging.basicConfig(filename='output.log', level=25)
logger = logging.getLogger(__name__)

_df = pd.core.frame.DataFrame


def augment_row_syn(row_id:int, text_df:_df, semehr_df:_df, augmemtation_prob=1):
    """
    Given a row ID of a discharge summary, the dataframe containing the discharge summaries, the dataframe of NER+L output (e.g, from semehr) reformatted with synonyms, and conversion of CUI to ICD9, and the probability with which each mention should be used for augmentation produces a new row with augmented text (with replacement synonyms) with the untouched gold standard.
    """
    mentions = semehr_df[semehr_df["row_id"]==row_id][["CUI", "string", "start_offset", "end_offset", "synonyms", "ICD9"]]
    original_row = text_df[text_df["ROW_ID"]==row_id]

    new_row = original_row.copy()
    # retrieve the original labels provided by the gold standard.
    labels = str(list(original_row["LABELS"])[0]).split(";")
    # retrieve the original text of the discharge summary.
    old_text = list(new_row.TEXT)[0]
    # initialise lists for the slices of interest and replacement code candidates.
    slices = []
    replacement_candidates = []
    # this loop prepares the relevant augmentation data structures -- identifies the relevant slices and their replacement texts
    for x, row in mentions.iterrows():
        if row.ICD9 in labels:
            if random.random()>=1-augmemtation_prob:
                logging.log(25, f"AUGMENTING LABEL {row.ICD9}")
                original_slice = (row["start_offset"], row["end_offset"])
                original_sliced_text = old_text[original_slice[0]:original_slice[1]].lower()
                all_replacement_candidates = row["synonyms"].split("|")
                all_replacement_candidates = [candidate.lower() for candidate in all_replacement_candidates]
                logging.log(25, str(len(all_replacement_candidates)) + ' candidates')
                # Assuming a candidate synonym is the same as the original text, this candidate synonym is removed.
                if original_sliced_text in all_replacement_candidates:
                    all_replacement_candidates.remove(original_sliced_text)
                # if there are some replacement synonyms left, prepare augmentation lists with a random synonym.
                if all_replacement_candidates !=[]:
                    replacement_text = choice(all_replacement_candidates)

                    slices.append((original_slice[0], original_slice[1]))
                    logging.log(25, f"{original_sliced_text} -> {replacement_text}")
                    replacement_candidates.append(replacement_text)
                    
    # execute the augmentation, replace the TEXT in the new row, return the row.
    new_row.TEXT = augment(old_text, slices, replacement_candidates)
    return(new_row)

def augment_all_rows_syn(intext:_df, semehr_output:_df)->_df:
    """
    Given a dataframe of discharge summaries, and their corresponding output of NER+L runs augmentation through synonyms on the whole dataframe.
    """
    logger.info(f'Initiating Augmentation.')
    new_rows = []
    counter = 0
    for id, row in tqdm(intext.iterrows()):
        new_row = augment_row_syn(row["ROW_ID"], intext, semehr_output)

        if new_row['TEXT'].iloc[0].lower().strip() != row.TEXT.lower().strip():
            counter+=1
        new_rows.append(new_row)
    logger.info(f'{counter} augmented rows')
    new_rows = pd.concat(new_rows)
    return new_rows
    
def run_augmentations(orignal_texts_df:_df, traditional_method_results:list)->_df:
    """
    Runs the synonym augmentation using outputs of different NER+L methods.
    """
    augmented_texts = []
    for single_method_results in traditional_method_results:
        augmented_texts.append(augment_all_rows_syn(orignal_texts_df, medcat_results))
    combined = pd.concat(augmented_texts)
    return combined

def synonym_lookup(code:str, synonym_df:_df)->str:
    """
    Returns a random synonym.
    """
    if len(synonym_df[synonym_df["LABEL"]==code].dropna())>0:
        return choice((synonym_df[synonym_df["LABEL"]==code].dropna().SYNONYMS.iloc[0]).split("|"))
    else:
        return None

    
def adj_lookup(code:str, conversion_table:_df, codeset:set)->str:
    """
    Returns a random adjacent code (belonging to a specific code subset).
    """
    assert codeset in ["normal", "few", "zero"]
    alts = conversion_table[conversion_table["code"]==code][codeset].dropna().iloc[0].split("|")
    return choice(alts)

def viable_sibling_check(code:str, df:_df, subset:set)->bool:
    """
    Checks for presence of viable siblings in a given subset
    """
    assert subset in {"normal", "few", "zero"}
    
    conversion_codes = set(list(df.code))
    if code not in conversion_codes:
        return False
    opstr = (df[df["code"]==code].iloc[0][subset])
    if str(opstr)=="nan":
        return False
    else:
        return len(opstr.split("|"))>0

def convert_labels(original_labels:list, conversion:_df, unspec:list)->dict:
    """
    Converts a list of gold standard labels to the new silver standard -- specified codes are only copied over, while ``unspecified'' codes are converted to sibling codes.
    Returns a dictionary indicating which gold stanard code maps to what silver standard code.
    """
    converted_labels = []
    label_map = dict()
    sets = ["zero", "few", "normal"]
    conversion_codes = list(conversion.code)
    for code in original_labels:
        s = "none"
        if code not in conversion_codes:
            label_map[code] = code
        else:
            if viable_sibling_check(code, conversion, "zero"):
                s = "zero"
            elif viable_sibling_check(code, conversion, "few"):
                s = "few"
            elif viable_sibling_check(code, conversion, "normal"):
                s = "normal"
            else:
            	s = "none"
            if code in unspec and (viable_sibling_check(code, conversion, s)):
                adj_code = adj_lookup(code, conversion, s)
                converted_labels.append(adj_code)
                label_map[code] = adj_code
            else:
                converted_labels.append(code)
                label_map[code] = code
    
    return label_map

def find_unspecifieds(convs:_df)->list:
    """
    Finds unspecified codes based a pre-made dataframe indicating family relationships/belonging to subgroups (from adjacent_setup.py) and a regular expression on ICD9 codes.
    """
    unspecifieds = []
    for ulist in convs.unspecified:
        if str(ulist) != "nan":
            unspecifieds+=ulist.split("|")
    unspecifieds = set(unspecifieds)

    pattern = ".+\.((9.?)|(.0)|(.1))$"
    pat = re.compile(pattern)
    unspecifieds = [u for u in unspecifieds if pat.match(u) is not None]
    return unspecifieds

def synth_row_adj(row_id:int, text_df:_df, semehr_df:_df, conversion_df:_df, synonym_df:_df, unspecs:list):
    """
    Performs synthesis on a document in the text dataframe identified by a row_id.
    """
    mentions = semehr_df[semehr_df["row_id"]==row_id][["CUI", "string", "start_offset", "end_offset", "synonyms", "ICD9"]]
    
    original_row = text_df[text_df["ROW_ID"]==row_id]
    new_row = original_row.copy()
    
    labels = str(list(original_row["LABELS"])[0]).strip().split(";")
    original_labels = set(labels)
    label_map = convert_labels(labels, conversion_df, unspecs)
    
    old_text = list(new_row.TEXT)[0]
    slices = []
    adjusted_labels = set()
    replacement_candidates = []
    
    # looping over mentions of the output of NER+L -- each row corresponds to one mention with an ICD9 code asigned.
    for x, row in mentions.iterrows():
    	# the synthesis is happening only for codes considered unspcefied.
        if row.ICD9 in labels and row.ICD9 in unspecs:
            slices.append((row["start_offset"], row["end_offset"]))
            # note that we are looking up synonyms for the replacement code as per the label_map, rather than for the original code
            replacement_candidate =  synonym_lookup(label_map[row.ICD9], synonym_df)
            if replacement_candidate is not None:
                replacement_candidates.append(replacement_candidate)
            adjusted_labels.add(row.ICD9)
    if replacement_candidates != []:
        new_row.TEXT = augment(old_text, slices, replacement_candidates)
        untouched_labels = original_labels.difference(adjusted_labels)
        new_labels = set([label_map[label] for label in adjusted_labels])
        new_label_set = untouched_labels.union(new_labels)
        new_label_string = ";".join(new_label_set)
        new_row["LABELS"] = new_label_string
        return(new_row)
    return None
    
def synth_all_rows_adj(intext:_df, semehr_output:_df, conversion_df:_df, synonym_df:_df)->_df:
    """
    Performs the adjacent-code synthesis on a full dataset.
    """
    new_rows = []
    counter = 0
    unspecs = find_unspecifieds(conversion_df)
    for id, row in tqdm(intext.iterrows()):
        new_row = synth_row_adj(row["ROW_ID"], intext, semehr_output, conversion_df, synonym_df, unspecs)
        if new_row is not None:
            if new_row['TEXT'].iloc[0].lower().strip() != row.TEXT.lower().strip():
                counter+=1
            new_rows.append(new_row)
    logger.info(f'{counter} synthetic rows')
    new_rows = pd.concat(new_rows)
    return new_rows
    
def run_synthesis_adj(orignal_texts_df:_df, traditional_method_results:list, conversion_df:_df, synonym_df:_df, iters =2)->_df:
    """
    Runs the whole synthesis pipeline over multiple iterations -- as there is randomness involved in choices of codes and of the replacement text for each mention, the same document can yield 
    multiple viable synths. Duplicates are dropped.
    """
    logger.info(f'Initiating Synthesis.')
    augmented_texts = []
    for single_method_results in traditional_method_results:
        for _ in range(iters):
            augmented_texts.append(synth_all_rows_adj(orignal_texts_df, medcat_results, conversion_df, synonym_df))
    combined = pd.concat(augmented_texts).drop_duplicates()
    return combined
    
    
if __name__ == "__main__":
    
    MIMIC_DIR = "/path/to/mimic/dir/" 
    AUG_FOLDER_RAW = "/path/to/the/raw/text/augmented/mimic/dir" 
    
    synonym_path = "/path/to/syns.csv"
    conversion_path = "path/to/conversion/table.csv"
    
    syn_df = pd.read_csv(synonym_path)
    conv_df = pd.read_csv(conversion_path)
    
    texts = pd.read_csv(MIMIC_DIR+"train_full_raw_wlabels.csv")
    print('texts read')
    
    semehr_results_path = "/path/to/semehr/results.csv"
    semehr_results = pd.read_csv(semehr_results_path)
    semehr_results = semehr_results.drop(columns=["Unnamed: 0"]).dropna()
    
    medcat_results_path = "/path/to/reformatted/mimic/results.csv"
    medcat_results = pd.read_csv(medcat_results_path)
    medcat_results = medcat_results.dropna()
    medcat_results = medcat_results.rename(columns=dict({"soure_value":"string","ROW_ID":"row_id","start":"start_offset", "end":"end_offset"}))
    
    # As randomness is involved, we recommend using seeds for reproducibility purposes.
    s = 50
    logger.info(f"Initialising augmentation with synonyms with seed {s}")
    seed(s)
    
    print('Augmentation')
    
    # Augmentation through synonyms
    semehr_augmented_texts = run_augmentations(texts, [semehr_results])
    medcat_augmented_texts = run_augmentations(texts, [medcat_results])
    
    medcat_augmented_texts.to_csv(AUG_FOLDER_RAW+"train_medcat_augmented_full_raw.csv",index=False)
    semehr_augmented_texts.to_csv(AUG_FOLDER_RAW+"train_semehr_augmented_full_raw.csv",index=False)
    
    print('Synthesis')
    
    # Synthesis with adjacent codes
    semehr_synth_texts = run_synthesis_adj(texts, [semehr_results], conv_df, syn_df, iters = 1)
    medcat_synth_texts = run_synthesis_adj(texts, [medcat_results], conv_df, syn_df, iters = 1)
    
    
    # Saving
    medcat_synth_texts.to_csv(AUG_FOLDER_RAW+"train_medcat_synthetic_full_raw.csv",index=False)
    semehr_synth_texts.to_csv(AUG_FOLDER_RAW+"train_semehr_synthetic_full_raw.csv",index=False)
    
