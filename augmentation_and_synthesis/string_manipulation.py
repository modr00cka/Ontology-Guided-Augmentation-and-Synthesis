def augment(original_string:str, original_slices:list, replacement_string_list:list)->str:
    """
    A simple text augmentation method -- given the original string, the slices where replacements are to be put, and the replacement string list produces the augmented text.
    """
    filler_indices = [0]
    for string_slice in original_slices:
        filler_indices += [string_slice[0], string_slice[1]]
    filler_indices.append(-1)
    
    filler_pairs = []
    for i in range(0,len(filler_indices),2):
        filler_pairs.append((filler_indices[i], filler_indices[i+1]))
        
    filler_strings = []
    for pair in filler_pairs:
        filler_strings.append(original_string[pair[0]:pair[1]])
    replacement_string_list_extended = replacement_string_list.copy()
    replacement_string_list_extended.append("")
    interleaved = [val for pair in zip(filler_strings, replacement_string_list_extended) for val in pair]
    full_replacement = "".join(interleaved)
    return full_replacement
    
if __name__ == "__main__":
    """
    Just a simple sample augmentation.
    """
    sample_string = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
    lorem = (0,5)
    print(sample_string[lorem[0]:lorem[1]])
    ipsum = (6,11)
    print(sample_string[ipsum[0]:ipsum[1]])
    dolor = (12,17)
    print(sample_string[dolor[0]:dolor[1]])
    sit = (18,21)
    print(sample_string[sit[0]:sit[1]])
    amet = (22,26)
    print(sample_string[amet[0]:amet[1]])
    
    original_strings = [lorem, ipsum, sit, amet]
    replacement_strings = ["The", "essential", "is", "invisible"]
    augmented_string = augment(sample_string, original_strings, replacement_strings)
    print(augmented_string)
