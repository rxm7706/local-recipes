print("""
    Running simplest example adapted from:

    https://github.com/huggingface/neuralcoref/blob/4.0.0/README.md#loading-neuralcoref

""")

# Load your usual SpaCy model (one of SpaCy English models)
import spacy
nlp = spacy.load('en_core_web_sm')

# Add neural coref to SpaCy's pipe
import neuralcoref
neuralcoref.add_to_pipe(nlp)

# You're done. You can now use NeuralCoref as you usually manipulate a SpaCy document annotations.
doc = nlp('My sister has a dog. She loves him.')

print(doc._.has_coref)
print(doc._.coref_clusters)
