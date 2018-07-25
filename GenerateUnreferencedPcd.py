'''
DetectNotUsedItem
'''
import re
import os
import shutil
import argparse

#
# Globals for help information
#
__prog__        = 'DetectNotUsedItem'
__version__     = '%s Version %s' % (__prog__, '0.1 ')
__copyright__   = 'Copyright (c) 2018, Intel Corporation. All rights reserved.'
__description__ = "Detect unreferenced PCD and GUID/Protocols/PPIs.\n"

class Common(object):

	def FindFileByExtendName(self, ExtendName, Path):
		Files = []
		for path in Path:
			for root, dirs, files in os.walk(path, topdown=True, followlinks=False):
				for name in files:
					if os.path.splitext(name)[-1].lower() == '.%s' % ExtendName:
						FullPath = os.path.join(root, name)
						Files.append(FullPath)
		return Files

	# Parse Dec and Inf file to get Line number and Pcd Name
	# return section name, the Pcdname and comments with there line number
	def ParseContent(self,File):
		SectionRE = re.compile(r'\[(.*)\]')
		ParseFlag = False
		Comments ={}
		comment_num = []
		SectionName = {}
		Name = {}
		with open(File, 'r') as F:
			for num, value in enumerate(F):
				Section = SectionRE.findall(value)
				if Section and not (value.strip().startswith("#")):
					section_name = Section[0]
					ParseFlag= self._InFlag(section_name)
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
							Name[num] = name
							Comments[name] = comment_num
							comment_num = []
		return SectionName, Name,Comments

	#Split the statement in Dec and Inf to get the PcdName
	def _split(self,value):
		return value.replace(' ','').split('=')[0].split('|')[0].split('#')[0].strip()

	def _InFlag(self,name):
		ParseFlag = False
	#	section =''
		ParsedSection = ["LibraryClasses", "Guids", "Ppis", "Protocols", "Pcd"]
		for section_keyword in ParsedSection:
			if section_keyword in name:
				ParseFlag = True
	#			section = name
		return ParseFlag

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
	def CheckPcd(self):
		unuse ={}
		DecSection, DecPcdName,DecComments = self.ParseDec()
		InfsDict = self.ParseInfFile()
		print("DEC File:\n%s"%self.Dec)
		print("Line Number%sUnused Item"%(" "*5))
		self.Log.append("DEC File:\n%s\nLine Number%sUnused PcdName\n"%(self.Dec,(" "*5)))
		for LineNum in list(DecPcdName.keys()):
			DecName = DecPcdName[LineNum]
			MatchFlag = False
			for Inf in InfsDict:
				Inf_dict = InfsDict[Inf]
				Inf_section_dict, InfPcdName_dict = Inf_dict
				for key in InfPcdName_dict.keys():
					InfName = InfPcdName_dict[key]
					if (DecName == InfName) or (DecName == InfName.split('.',1)[0]):
						MatchFlag = True
			if MatchFlag == False:
				unuse[LineNum] = DecName
				print("%s%s%s"%("{:>6}".format(LineNum+1)," "*12,DecName))
				self.Log.append("%s%s%s\n"%("{:>6}".format(LineNum+1)," "*12,DecName))
		self.Log.append("\n")
		self.AppendSectionInfoToLog(DecSection,unuse)
		return unuse,DecComments

	def AppendSectionInfoToLog(self,DecSection,UnuseDict):
		pass
		for Name_num in list(UnuseDict.keys()):
			section_list = list(sorted(DecSection.keys()))
			for Section_num in section_list:
				if Name_num < Section_num:
					Section = DecSection[section_list[section_list.index(Section_num)-1]]
					break
		pass


	#Clean the Pcd from Dec file which not used in Inf file.
	#The origin Dec file will rename to DecFile.bak
	def Clean(self, UnUseDict, Comments):
		removednum = []
		for num in list(UnUseDict.keys()):
			pcd = UnUseDict[num]
			if pcd in list(Comments.keys()):
				removednum += Comments[pcd]
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
			print("New Dec File Name:%s, origin Dec File Name:%s.bak"%(self.Dec,self.Dec))
		except Exception as err:
			print(err)

class Main(object):

	def mainprocess(self,Dec, Dirs, CleanFlag, LogPath):
		R = PROCESS(Dec,Dirs)
		unuse, comment = R.CheckPcd()
		self.WriteLog(R.Log, LogPath)
		if CleanFlag:
			R.Clean(unuse, comment)

	# Function for Write log to log file.
	def WriteLog(self,content, FileName):
		if FileName != False:
			try:
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
	parser.add_argument('--dirs', metavar="", action='append', dest='dirs', help="Input dir/dirs which include the INF file.")
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