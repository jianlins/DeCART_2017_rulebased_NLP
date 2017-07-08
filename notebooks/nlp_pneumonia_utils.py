import zipfile
import codecs
import sklearn.metrics
import pandas as pd

# this class encapsulates all data related to a span (text sequence) annotation
# including the text it "covers" and the type (i.e. "concept") of the annotation
class Annotation(object):
    def __init__(self):
        self.start_index = -1
        self.end_index = -1
        self.type = ''
        self.spanned_text = ''
        
    # adding this so that pyConText's HTML markup can work seamlessly
    def getSpan(self):
        return (self.start_index, self.end_index)
    
    def getCategory(self):
        # pyConText graph objects actually expect a list here
        return [self.type]

# this class encapsulates all data for a document which has been annotated_doc_map
# this includes the original text, its annotations and also 
class AnnotatedDocument(object):
    def __init__(self):
        self.text = ''
        self.annotations = []
        # NOTE : This "positive_label" relates to positive/possible cases of pneumonia
        self.positive_label = -1
        
def read_brat_annotations(lines):
    annotations = []
    # BRAT FORMAT is:
    # NUMBER[TAB]TYPE[SPACE]START_INDEX[SPACE]END_INDEX[SPACE]SPANNED_TEXT
    for line in lines:
        line = str(line)
        tab_tokens = line.split('\t')
        space_tokens = tab_tokens[1].split()
        anno = Annotation()
        anno.spanned_text = tab_tokens[-1]
        anno.type = space_tokens[0]
        anno.start_index = int(space_tokens[1])
        anno.end_index = int(space_tokens[2])
        annotations.append(anno)
    return annotations
        
def read_annotations(archive_file, force_redownload = False):
    print('Reading annotations from file : ' + archive_file)
    filename = archive_file.split('/')[-1]
    
    if 'http' in archive_file:
        if force_redownload or not os.path.isfile(filename):
            print('Downloading remote file : '+ archive_file)
            urllib.request.urlretrieve(archive_file, filename)
    
    annotated_doc_map = {}
    
    print('Opening local file : ' + filename)
    z = zipfile.ZipFile(filename, "r")
    zinfo = z.namelist()
    for name in zinfo:
        if name.endswith('.txt') or name.endswith('.ann'):
            basename = name.split('.')[0]
            if basename not in annotated_doc_map:
                annotated_doc_map[basename] = AnnotatedDocument()
            anno_doc = annotated_doc_map[basename]
            # handle text and BRAT annotation files (.ann) differently
            if name.endswith('.txt'):
                with z.open(name) as f1:
                    anno_doc.text = f1.read().decode('utf8')
            else:
                with z.open(name) as f1:
                    # handle this as utf8 or we get back byte arrays
                    anno_doc.annotations = read_brat_annotations(codecs.iterdecode(f1, 'utf8'))
                    
    # now let's finally assign a 0 or 1 to each document based on whether we see our expected type for the pneumonia label
    for key, anno_doc in annotated_doc_map.items():
        annos = anno_doc.annotations
        anno_doc.positive_label = 0
        for anno in annos:
            # NOTE : This "positive_label" relates to positive/possible cases of pneumonia
            if anno.type == 'DOCUMENT_PNEUMONIA_YES':
                anno_doc.positive_label = 1
                    
    return list(annotated_doc_map.values())

def calculate_prediction_metrics(gold_docs, prediction_function):
    gold_labels = [x.positive_label for x in gold_docs]
    pred_labels = []
    for gold_doc in gold_docs:
        pred_label = prediction_function(gold_doc.text)
        pred_labels.append(pred_label)
        
    # now let's use scikit-learn to compute some metrics
    precision = sklearn.metrics.precision_score(gold_labels, pred_labels)
    recall = sklearn.metrics.recall_score(gold_labels, pred_labels)
    f1 = sklearn.metrics.f1_score(gold_labels, pred_labels)
    # let's use Pandas to make a confusion matrix for us
    confusion_matrix_df = pd.crosstab(pd.Series(gold_labels, name = 'Actual'), 
                                      pd.Series(pred_labels, name = 'Predicted'))
    
    print('Precision : {0}'.format(precision))
    print('Recall : {0}'.format(recall))
    print('F1: {0}'.format(f1))
    
    print('Confusion Matrix : ')
    print(confusion_matrix_df)

# helper functions to highlight annotations from BRAT
def mark_text(txt,nodes,colors = {"name":"red","pet":"blue"},default_color="black"):
    from pyConTextNLP.display.html import __insert_color
    # this function had to be copied and modified from pyConTextNLP.display.html.mark_text 
    # so that the default_color could be passed through
    if not nodes:
        return txt
    else:
        n = nodes.pop(-1)
        return mark_text(__insert_color(txt,
                                        n.getSpan(),
                                        colors.get(n.getCategory()[0],default_color)),
                         nodes,
                         colors=colors,
                         # this was not being passed through 
                        default_color = default_color)
    
def pneumonia_html_markup(anno_doc):
    from pyConTextNLP.display.html import __sort_by_span
    # this bit mimics 'mark_document_with_html' from pyConTextNLP.display.html
    colors = {}
    colors['DOCUMENT_PNEUMONIA_YES'] = 'red'
    colors['DOCUMENT_PNEUMONIA_NO'] = 'green'
    colors['SPAN_POSITIVE_PNEUMONIA_EVIDENCE'] = 'red'
    default_color = 'red'
    html = """<p> {0} </p>""".format(" ".join([mark_text(anno_doc.text,
                                                 __sort_by_span(anno_doc.annotations),
                                                 colors=colors,
                                                 default_color=default_color)]))
    return html