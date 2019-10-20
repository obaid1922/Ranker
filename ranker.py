import regex
from xml.dom import minidom
from nltk.stem import PorterStemmer
import math


def readHashInvertedIndex(offset):
    docHash = {}
    stats = {}
    file = open("term_index.txt", 'r')
    file.seek(offset)
    posting = file.readline()
    entries = posting.split(sep=" ")
    previousDoc = 0
    previousPosition = 0
    currentDoc = int(entries[3].split(",")[0])
    currentPosition = int(entries[3].split(",")[1])
    previousDoc = currentDoc
    previousPosition = currentPosition
    statList = [int(entries[1]), int(entries[2])]
    stats[int(entries[0])] = statList
    if currentDoc in docHash:
        tempList = docHash[currentDoc]
        tempList.append(currentPosition)
    else:
        tempList = [currentPosition]
        docHash[currentDoc] = tempList
    for i in range(4, len(entries)):
        decodedDoc = int(entries[i].split(",")[0]) + previousDoc

        if decodedDoc != previousDoc:
            previousPosition = 0
        decodedPosition = int(entries[i].split(",")[1]) + previousPosition
        if decodedDoc in docHash:
            tempList = docHash[decodedDoc]
            tempList.append(decodedPosition)
        else:
            tempList = [decodedPosition]
            docHash[decodedDoc] = tempList
        previousDoc = decodedDoc
        previousPosition = decodedPosition
    file.close()
    return docHash, stats


def readOffset():
    offsets = {}
    fileContents = open("term_info.txt", 'r').read().splitlines()
    for dictEntry in fileContents:
        key = int(dictEntry.split("\t")[0])
        value = int(dictEntry.split("\t")[1])
        offsets[key] = value
    return offsets


def readVocabulary():
    vocabulary = {}
    fileContents = open("termids.txt", 'r').read().splitlines()
    for dictEntry in fileContents:
        key = dictEntry.split("\t")[1]
        value = int(dictEntry.split("\t")[0])
        vocabulary[key] = value
    return vocabulary


def readDocIds():
    docIds = {}
    fileContents = open("docids.txt", 'r').read().splitlines()
    for dictEntry in fileContents:
        key = dictEntry.split("\t")[1]
        if ".txt" in key:
            key = key.replace(".txt", "")
        if ".html" in key:
            key = key.replace(".html", "")
        value = int(dictEntry.split("\t")[0])
        docIds[key] = value
    return docIds


def termDocInfo():
    docinfo = {}
    sum = 0
    fileContents = open("docinfo.txt", 'r').read().splitlines()
    for dictEntry in fileContents:
        key = int(dictEntry.split("\t")[2])
        doclen = int(dictEntry.split("\t")[0])
        docuniq = int(dictEntry.split("\t")[1])
        docinfo[key] = [doclen, docuniq]
        sum += doclen
    avg = sum / len(docinfo)
    return docinfo, avg


xmldoc = minidom.parse('topics.xml')
topics = xmldoc.getElementsByTagName('query')
stopFile = set(open("stoplist.txt").read().splitlines())
queries = {}
for query in topics:
    data = query.firstChild.data
    number = int(query.parentNode.attributes['number'].value)
    words = regex.findall(r"\b[0-9A-Za-z]+(?:['-]?[0-9A-Za-z]+)*\b", data)
    qrep = {}
    for token in words:
        if token not in stopFile:
            token = PorterStemmer().stem(token)
            if token not in qrep:
                qrep[token] = 1
            else:
                tcount = qrep[token]
                tcount += 1
                qrep[token] = tcount
    queries[number] = qrep


def languageModelRanking(queries, wordindices, wordstats, docinfo, avg, docs, vocab):
    probabilityDist = []
    rankings = {}
    for inquery in queries:
        for doc in docs:
            probability = 1

            for qterm in queries[inquery]:
                a1 = 0
                a2 = 0
                if docs[doc] in wordindices[vocab[qterm]]:
                    occurences = len(wordindices[vocab[qterm]][docs[doc]])
                else:
                    occurences = 0
                if docinfo[docs[doc]][0] != 0:
                    a1 = ((docinfo[docs[doc]][0]) / (docinfo[docs[doc]][0] + avg)) * (
                            occurences / docinfo[docs[doc]][0])
                a2 = (avg / (docinfo[docs[doc]][0] + avg)) * (wordstats[vocab[qterm]][0] / len(vocab))
                total = a1 + a2
                probability = float(probability) * float(total)
            if inquery not in rankings:
                rankings[inquery] = [(probability, doc)]
            else:
                ranks = rankings[inquery]
                ranks.append((probability, doc))
                rankings[inquery] = ranks
    for query in rankings:
        tlist = rankings[query]
        tlist.sort(key=lambda t: t[0], reverse=True)
        rankings[query] = tlist
    return rankings


def bm25Ranking(queries, wordindices, wordstats, docinfo, avg, docs, kval):
    tf = -1
    idf = -1
    bm25scores = []
    k1 = 1.2
    k2 = kval
    print(k2)
    b = 0.75
    print()
    rankings = {}
    for inquery in queries:
        for doc in docs:
            bm25score = 0
            for qterm in queries[inquery]:
                if docs[doc] in wordindices[vocab[qterm]]:
                    tf = 1 + math.log10(len(wordindices[vocab[qterm]][docs[doc]]))
                else:
                    tf = 0
                idf = 1 + (len(docs) / wordstats[vocab[qterm]][1])
                K = k1 * ((1 - b) + (b * (docinfo[docs[doc]][0] / avg)))
                a = math.log10((len(docs) + 0.5) / (wordstats[vocab[qterm]][1] + 0.5))
                a1 = ((1 + k1) * tf) / (K + tf)
                a2 = ((1 + k2) * queries[inquery][qterm]) / (k2 + queries[inquery][qterm])
                if a2 != 1.0:
                    print("YEEEET!!!!!!!!!!!!!!!")
                bm25score += a * a1 * a2

            if inquery not in rankings:
                rankings[inquery] = [(bm25score, doc)]
            else:
                ranks = rankings[inquery]
                ranks.append((bm25score, doc))
                rankings[inquery] = ranks

    for query in rankings:
        tlist = rankings[query]
        tlist.sort(key=lambda t: t[0], reverse=True)
        rankings[query] = tlist
    return rankings


def readEvaluations():
    fd = open("relevance judgements.qrel", "r")
    contents = fd.read().splitlines()
    currentquery = int(contents[0].split(" ")[0])
    previousquery = currentquery
    innerdict = {}
    judgments = {}
    releventDocs = 0
    for entry in contents:
        evaluation = entry.split(" ")
        docname = evaluation[2]
        relevence = int(evaluation[3])
        if relevence > 0:
            relevence = 1
            releventDocs += 1
        else:
            relevence = 0
        previousquery = currentquery
        currentquery = int(evaluation[0])
        if previousquery != currentquery:
            judgments[previousquery] = [innerdict, releventDocs]
            innerdict = {}
            releventDocs = 0
            innerdict[docname] = relevence
        else:
            innerdict[docname] = relevence
    judgments[previousquery] = [innerdict, releventDocs]
    return judgments


def evaluateMAP(rankedList, judgments):
    p = 30
    precisisionK = -1
    total = 0
    for query in rankedList:
        relevent = 0
        for i in range(p):
            doc = rankedList[query][i][1]
            if doc in judgements[query][0]:
                if judgements[query][0][doc] == 1:
                    relevent += 1
        precisisionK = relevent / p
        print(precisisionK)
        total += precisisionK
    # print(total / len(rankedList))


offsets = readOffset()
vocab = readVocabulary()
docs = readDocIds()
judgements = readEvaluations()
wordindices = {}
wordstats = {}
i = 0
docinfo, avg = termDocInfo()
for inquery in queries:
    queryterms = queries[inquery]
    for query in queryterms:
        wordindex, wordstat = readHashInvertedIndex(offsets[vocab[query]])
        wordindices[vocab[query]] = wordindex
        wordstats[vocab[query]] = wordstat[vocab[query]]
    # for k2 in range(0, 1000, 2):
rankedList = bm25Ranking(queries, wordindices, wordstats, docinfo, avg, docs, 500)
# rankedListLM = languageModelRanking(queries, wordindices, wordstats, docinfo, avg, docs, vocab)
for x in rankedList[250]:
    if x[1] == 'clueweb12-0101wb-39-29794':
        print(x[0])
# evaluateMAP(rankedList, judgements)
