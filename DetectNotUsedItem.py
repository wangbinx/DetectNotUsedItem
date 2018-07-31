## @file
# Detect unreferenced PCD and GUID/Protocols/PPIs.
#
# Copyright (c) 2018, Intel Corporation. All rights reserved.<BR>
# This program and the accompanying materials
# are licensed and made available under the terms and conditions of the BSD License
# which accompanies this distribution.  The full text of the license may be found at
# http://opensource.org/licenses/bsd-license.php
#
# THE PROGRAM IS DISTRIBUTED UNDER THE BSD LICENSE ON AN "AS IS" BASIS,
# WITHOUT WARRANTIES OR REPRESENTATIONS OF ANY KIND, EITHER EXPRESS OR IMPLIED.
#

'''
DetectNotUsedItem
'''
import re
import os
import sys
import shutil
import argparse

#
# Globals for help information
#
__prog__        = 'DetectNotUsedItem'
__version__     = '%s Version %s' % (__prog__, '0.2 ')
__copyright__   = 'Copyright (c) 2018, Intel Corporation. All rights reserved.'
__description__ = "Detect unreferenced PCD and GUID/Protocols/PPIs.\n"

class Common(object):

	def FindFileByExtendName(self, ExtendName, Path):
		Files = []
		for path in Path:
			for root, dirs, files in os.walk(path, topdown=True, followlinks=False):
				for name in files:
					if name.endswith(ExtendName):
						FullPath = os.path.join(root, name)
						Files.append(FullPath)
		return Files

	# Parse Dec and Inf file to get Line number and Pcd Name
	# return section name, the Item Name and comments with there line number
	def ParseContent(self,File):
		SectionRE = re.compile(r'\[(.*)\]')
		ParseFlag = False
		Comments ={}
		comment_num = []
		SectionName = {}
		ItemName = {}
		with open(File, 'r') as F:
			for num, value in enumerate(F):
				Section = SectionRE.findall(value)
				if Section and not (value.strip().startswith("#")):
					section_name = Section[0]
					ParseFlag= self._InSectionFlag(section_name)
					SectionName[num] = section_name
					continue
				if ParseFlag == True:
					if value.strip().startswith("#"):
						CommentsFlag = True
					else:
						CommentsFlag = False
					if CommentsFlag:
						comment_num.append(num)
					if not (value.strip().startswith("#")):
						comment_num.append(num)
						if not value == "\n":
							name = self._split(value)
							ItemName[num] = name
							Comments[num] = comment_num
							comment_num = []
		return SectionName, ItemName,Comments

	#Split the statement in Dec and Inf to get the ItemName
	def _split(self,value):
		return value.replace(' ','').split('=')[0].split('|')[0].split('#')[0].strip()


	def _InSectionFlag(self,name):
		InFlag = False
		ParsedSectionKeyWord = ["LibraryClasses", "Guids", "Ppis", "Protocols", "Pcd"]
		for keyword in ParsedSectionKeyWord:
			if keyword in name:
				InFlag = True
		return InFlag

class PROCESS(Common):

	def __init__(self,DecPath,InfDirs):
		self.Dec = DecPath
		self.InfPath = InfDirs
		#Save output information to self.Log
		self.Log = []

	def ParseDec(self):
		Section, Pcd,Comments = self.ParseContent(self.Dec)
		return Section, Pcd, Comments

	#Find all Inf file in dirs to generate name
	def FindInf(self):
		InfList=self.FindFileByExtendName("inf",self.InfPath)
		return InfList

	def ParseInfFile(self):
		INF_Dict ={}
		for inf in self.FindInf():
			tmp_Section,tmp_Pcd,tmp_Comments = self.ParseContent(inf)
			INF_Dict[inf] = tmp_Section,tmp_Pcd
		return INF_Dict

	#Compare the LibraryClass/Guid/PcdCname in Dec and LibraryClass/Guid/PcdCname in Inf, if not equal, save the
	#Pcd name, the Line number, and it's comments
	def CompareNamebetweenDecAndInf(self):
		unuse ={}
		DecSection, DecItem, DecComments = self.ParseDec()
		InfsDict = self.ParseInfFile()
		for LineNum in list(DecItem.keys()):
			DecItemName = DecItem[LineNum]
			MatchFlag = False
			for Inf in InfsDict:
				Inf_dict = InfsDict[Inf]
				Inf_section, InfItem_dict = Inf_dict
				for key in InfItem_dict.keys():
					InfItemName = InfItem_dict[key]
					if (DecItemName == InfItemName) or (DecItemName == InfItemName.split('.',1)[0]):
						MatchFlag = True
			if MatchFlag == False:
				unuse[LineNum] = DecItemName
		self.LogClassify(DecSection,unuse)
		return unuse,DecComments


	def LogClassify(self,DecSection,UnuseDict):
		# Set default length for output alignment
		minlen = 16
		Dict = {}
		for Name_num in list(UnuseDict.keys()):
			section_list = list(sorted(DecSection.keys()))
			for Section_num in section_list:
				if Name_num < Section_num:
					Section = DecSection[section_list[section_list.index(Section_num)-1]]
					minlen = max(minlen,len(Section))
					tmp =[UnuseDict[Name_num],Section]
					Dict[Name_num] = tmp
					break
		print("DEC File:\n%s\n%s%s%s" % (self.Dec, ("{:<%s}"%(minlen-1)).format("Section Name"), "{:<15}".format("Line Number"), "{:<0}".format("Unused Item")))
		self.Log.append("DEC File:\n%s\n%s%s%s\n" % (self.Dec, ("{:<%s}"%(minlen-1)).format("Section Name"), "{:<15}".format("Line Number"), "{:<0}".format("Unused Item")))
		for num in list(sorted(Dict.keys())):
			ItemName,Section = Dict[num]
			print("%s%s%s" % (("{:<%s}"%(minlen+2)).format(Section), "{:<12}".format(num + 1), "{:<1}".format(ItemName)))
			self.Log.append("%s%s%s\n" % (("{:<%s}"%(minlen+2)).format(Section), "{:<12}".format(num + 1), "{:<1}".format(ItemName)))

	#Clean the Pcd from Dec file which not used in Inf file.
	#The origin Dec file will rename to DecFile.bak
	def Clean(self, UnUseDict, Comments):
		removednum = []
		for num in list(UnUseDict.keys()):
			if num in list(Comments.keys()):
				removednum += Comments[num]
		with open(self.Dec, 'r') as Dec:
			lines = Dec.readlines()
		shutil.copyfile(self.Dec,self.Dec+'.bak')
		try:
			with open(self.Dec, 'w+') as T:
				for linenum in range(len(lines)):
					if linenum in removednum:
						continue
					else:
						T.write(lines[linenum])
			print("New Dec File is %s, backup origin Dec to %s.bak"%(self.Dec,self.Dec))
		except Exception as err:
			print(err)

class Main(object):

	def mainprocess(self, Dec, Dirs, CleanFlag, LogPath):
		if not (os.path.exists(Dec) and Dec.endswith(".dec")):
			print("ERROR:Invalid DEC file input: %s"%Dec)
			sys.exit(1)
		for  dir in Dirs:
			if not os.path.exists(dir):
				print("ERROR:Invalid DIR for '--dirs': %s"%dir)
				sys.exit(1)
		run = PROCESS(Dec,Dirs)
		unuse, comment = run.CompareNamebetweenDecAndInf()
		self.WriteLog(run.Log, LogPath)
		if CleanFlag:
			run.Clean(unuse, comment)

	# Function for Write log to log file.
	def WriteLog(self,content, FileName):
		if FileName != False:
			try:
				#if Filename is a path, create path
				if "\\" in FileName:
					List = FileName.split('\\')
					FilePath = "\\".join(List[:-1])
					if not os.path.exists(FilePath):
						os.makedirs(FilePath)
				with open(FileName, 'w+') as log:
					for line in content:
						log.write(line)
				print("Log save to file:%s" %FileName)
				log.close()
			except Exception as e:
				print("Save log Error:%s"%e)

def main():
	parser = argparse.ArgumentParser(prog=__prog__,
		                            description=__description__ + __copyright__,
		                            conflict_handler='resolve')
	parser.add_argument('-i', '--input', metavar="", dest='dec',help="Input DEC file path.")
	parser.add_argument('--dirs', metavar="", action='append', dest='dirs', help="Input the package dir/dirs.")
	parser.add_argument('--clean', action = 'store_true', default=False, dest='clean', help="Clean the unreferenced PCD from DEC file.")
	parser.add_argument('--log', metavar="", dest="log", default=False,help="Export log to file")
	options = parser.parse_args()
	if options.dec:
		if options.dirs:
			M = Main()
			M.mainprocess(options.dec,options.dirs,options.clean,options.log)
		else:
			print("Error: the following argument is required:'--dirs', please see '-h' for help")
	else:
		print("Error: the following argument is required:'-i', please see '-h' for help")

if __name__ == '__main__':
	main()