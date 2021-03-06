import sys
import json
import time
import numpy as np

from sklearn.externals import joblib
from functools import reduce

from Retrieval import Retrieval
from Featurizer import Featurizer
from CountFeaturizer import CountFeaturizer
from TfIdfFeaturizer import TfIdfFeaturizer
from Classifier import Classifier
from MultiLayerPerceptron import MultiLayerPerceptron
from MultinomialNaiveBayes import MultinomialNaiveBayes
from SupportVectorMachine import SupportVectorMachine
from Evaluator import Evaluator


TRAINING_DATA={
	'test_size' : 1000
}

VAL_DATA = {
	'test_size' : 1000
}

class Pipeline(object):
	def __init__(self, trainFilePath, valFilePath, retrievalInstance, featurizerInstance, classifierInstance):
		self.retrievalInstance = retrievalInstance
		self.featurizerInstances = featurizerInstances
		self.classifierInstances = classifierInstances
		trainfile = open(trainFilePath, 'r')
		self.trainData = json.load(trainfile)
		trainfile.close()
		valfile = open(valFilePath, 'r')
		self.valData = json.load(valfile)
		valfile.close()
		self.question_answering()
		self.genarate_analysis()
		outfile = open("resultsTable.html","w")
		outfile.write(self.generate_html(self.result))
		outfile.close()

	def makeXY(self, dataQuestions):
		X = []
		Y = []
		for question in dataQuestions:
			long_snippets = self.retrievalInstance.getLongSnippets(question)
			short_snippets = self.retrievalInstance.getShortSnippets(question)
			X.append(short_snippets)
			Y.append(question['answers'][0])
		return X, Y


	def question_answering(self):
		dataset_type = self.trainData['origin']
		candidate_answers = self.trainData['candidates']
		X_train, Y_train = self.makeXY(self.trainData['questions'][0:TRAINING_DATA['test_size']])
		X_val, Y_val_true = self.makeXY(self.valData['questions'][0:VAL_DATA['test_size']])
		np_Y_val_true = np.array(Y_val_true)

		self.correct_answers = {}
		self.result = [['Featurizer','Classifier','Accuracy','Precision','Recall','F-Measure']]
		for featurizerInstance in featurizerInstances:
			print("Features Created for :" + featurizerInstance.getName())
			X_features_train, X_features_val = featurizerInstance.getFeatureRepresentation(X_train, X_val)
			for classifierInstance in classifierInstances:
				#featurization
				clf = classifierInstance.buildClassifier(X_features_train, Y_train)
				print("Classifier Created for :" + classifierInstance.getName())
				#Prediction
				Y_val_pred = clf.predict(X_features_val)
				np_Y_val_pred = np.array(Y_val_pred)
				correct_answers_elem = [Y_val_pred[i] == Y_val_true[i] for i in range(len(Y_val_true))]
				self.correct_answers[featurizerInstance.getName()+'|'+classifierInstance.getName()] = correct_answers_elem
				self.evaluatorInstance = Evaluator()
				a =  self.evaluatorInstance.getAccuracy(Y_val_true, Y_val_pred)
				p,r,f = self.evaluatorInstance.getPRF(Y_val_true, Y_val_pred)
				self.result.append([featurizerInstance.getName(),classifierInstance.getName(),str(a),str(p),str(r),str(f)])

	def genarate_analysis(self) :
		ts = time.gmtime()
		tsf = time.strftime("%Y-%m-%d %H:%M:%S", ts)
		table = "<html><head><title>Comparison Analysis</title></head><body><h1>" + tsf + " QA Pipeline with Learning - Comparison Analysis</h1>\n\n"
		table = table + '<br></br><br></br><br></br><p> Training size'+ str(TRAINING_DATA['test_size']) +'</p>'
		table = table + '<br></br><p> Validation size'+ str(VAL_DATA['test_size']) +'</p>'

		self.report_analysis = []
		completed_pairs = []
		for akey, avalue  in self.correct_answers.items():
			completed_pairs.append(akey)
			for bkey, bvalue  in self.correct_answers.items():
				if bkey in completed_pairs:
					continue
				else:
					arr00 = []
					arr11 = []
					arr01 = []
					arr10 = []
					for i in range(len(avalue)):
						if avalue[i] == True and bvalue[i] == True:
							arr11.append(i)
						elif avalue[i] == True and bvalue[i] == False:
							arr10.append(i)
						elif avalue[i] == False and bvalue[i] == True:
							arr01.append(i)
						else:
							arr00.append(i)

					self.report_analysis.append((akey,bkey,arr00,arr01,arr10,arr11))

					table = table + "<br></br><br></br><br></br>\n\n"
					table = table + '<h2>S : Classifier : ' + akey.split('|')[0] + ' Featurizer :' + akey.split('|')[1] + '</h2>\n\n'
					table = table + '<h2>S* : Classifier : ' + bkey.split('|')[0] + ' Featurizer :' + bkey.split('|')[1] + '</h2>\n\n'
					table = table + "<p>"+'No.of Tough Inputs' + str(len(arr00))+"</p>\n\n"
					table = table + "<p>"+'No.of Easy Inputs' + str(len(arr11))+"</p>\n\n"
					table = table + "<p>"+'No.of Improvements' + str(len(arr01))+"</p>\n\n"
					table = table + "<p>"+'No.of Regeression' + str(len(arr10))+"</p>\n\n"

					print('Comparison Between :-')
					print('S : Classifier : ' + akey.split('|')[0] + ' Featurizer :' + akey.split('|')[1])
					print('S* : Classifier : ' + bkey.split('|')[0] + ' Featurizer :' + bkey.split('|')[1])
					print('No.of Tough Inputs' + str(len(arr00)))
					print('No.of Easy Inputs' + str(len(arr11)))
					print('No.of Improvements' + str(len(arr01)))
					print('No.of Regeression' + str(len(arr10)))
					print('\n\n\n')

		table = table + self.find_tough_for_all()
		table = table + self.find_easy_for_all()
		table += "</body>\n</html>\n";
		outfile = open("resultsAnalysis.html","w")
		outfile.write(table)
		outfile.close()


	def find_tough_for_all(self):

		parent_arr = list(range(len(self.valData['questions'][0:VAL_DATA['test_size']])))
		for analysis in self.report_analysis:
			parent_arr = np.intersect1d(parent_arr,analysis[2]).tolist()

		print("\n Indexes of Tough Questions for all models : \n")
		print(parent_arr)
		table = '<h1>\n Indexes of Tough Questions for all models : \n</h1>'
		table = table + '<p>' + str(parent_arr)+'</p>'
		table = table + '<p> Total Number of tough Questions: ' + str(len(parent_arr))+'</p>'

		if len(parent_arr) < 1:
			table = table + '<p>No Tough Questions Available</p>'
			return table
		print("\n Example of Tough Question at index 0 : \n")
		print(self.retrievalInstance.getShortSnippets(self.valData['questions'][parent_arr[0]]))
		table = table + '<h1>\n Example of Tough Question at index 0 : \n</h1>'
		table = table + '<p>' + str(self.retrievalInstance.getShortSnippets(self.valData['questions'][parent_arr[0]]))+'</p>'

		if len(parent_arr) < 2:
			return table
		print("\n Example of Tough Question at index 1 : \n")
		print(self.retrievalInstance.getShortSnippets(self.valData['questions'][parent_arr[1]]))
		table = table + '<h1>\n Example of Tough Question at index 1 : \n</h1>'
		table = table + '<p>' + str(self.retrievalInstance.getShortSnippets(self.valData['questions'][parent_arr[1]]))+'</p>'
		return table

	def find_easy_for_all(self):
		parent_arr = list(range(len(self.valData['questions'][0:VAL_DATA['test_size']])))
		for analysis in self.report_analysis:
			parent_arr = np.intersect1d(parent_arr,analysis[5]).tolist()
		print("\n Indexes of Easy Questions for all models : \n")
		print(parent_arr)
		table = '<h1>\n Indexes of Easy Questions for all models : \n</h1>'
		table = table + '<p>' + str(parent_arr)+'</p>'
		table = table + '<p> Total Number of Easy Questions: ' + str(len(parent_arr))+'</p>'

		if len(parent_arr) < 1:
			table = table + '<p>No Easy Questions Available</p>'
			return table
		print("\n Example of Easy Question at index 0 : \n")
		print(self.retrievalInstance.getShortSnippets(self.valData['questions'][parent_arr[0]]))
		table = table + '<h1>\n Example of Easy Question at index 0 : \n</h1>'
		table = table + '<p>' + str(self.retrievalInstance.getShortSnippets(self.valData['questions'][parent_arr[0]]))+'</p>'

		if len(parent_arr) < 2:
			return table
		print("\n Example of Easy Question at index 1 : \n")
		print(self.retrievalInstance.getShortSnippets(self.valData['questions'][parent_arr[1]]))
		table = table + '<h1>\n Example of Easy Question at index 1 : \n</h1>'
		table = table + '<p>' + str(self.retrievalInstance.getShortSnippets(self.valData['questions'][parent_arr[1]]))+'</p>'
		return table

	def generate_html(self,result):
		ts = time.gmtime()
		tsf = time.strftime("%Y-%m-%d %H:%M:%S", ts)
		table = "<html><head><title>QA Pipeline with Learning " + tsf + "</title><link href=\"results.css\" rel=\"stylesheet\"></head><body><h2>" + tsf + " QA Pipeline with Learning</h2>\n"
		table = table + '<br></br><br></br><br></br><p> Training size'+ str(TRAINING_DATA['test_size']) +'</p>'
		table = table + '<br></br><p> Validation size'+ str(VAL_DATA['test_size']) +'</p>'
		table =  table + "<table>\n"
		for i,each_result in enumerate(result):
			table += "<tr>"
			if i == 0 :
				for val in each_result:
					table += "<th>" + val + "</th>"
			else:
				for val in each_result:
					table += "<td>" + val + "</td>"
			table += "</tr>"
		table += "</table>\n</body>\n</html>\n";
		return table

if __name__ == '__main__':
	trainFilePath = sys.argv[1] #please give the path to your reformatted quasar-s json train file
	valFilePath = sys.argv[2] # provide the path to val file
	retrievalInstance = Retrieval()
	featurizerInstances = [CountFeaturizer(),TfIdfFeaturizer()]
	classifierInstances = [MultinomialNaiveBayes(),MultiLayerPerceptron(),SupportVectorMachine()]
	trainInstance = Pipeline(trainFilePath, valFilePath, retrievalInstance, featurizerInstances, classifierInstances)
