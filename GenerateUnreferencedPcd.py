import re
import os
import shutil
import argparse

#
# Globals for help information
#
__prog__        = 'GenerateUnreferencedPcd'
__version__     = '%s Version %s' % (__prog__, '0.1 ')
__copyright__   = 'Copyright (c) 2016 - 2018, Intel Corporation. All rights reserved.'
__description__ = "Generate all Unreferenced Pcd in Dec File, echo the DEC file, the pcd name and it's line number.\n"

class PROCESS(object):

	def __init__(self,DecPathDict):
		self.Dec = list(DecPathDict.keys())[0]
		self.Path = DecPathDict[self.Dec]
		#Save output information to self.Log
		self.Log = []

	#Parse Dec and Inf file to get Line number and Pcd Name
	#return section name, the Pcdname and comments with there line number
	def ParseContent(self,File):
		SectionRE = re.compile(r'\[(.*)\]')
		ParseFlag = False
		Comments ={}
		comment = []
		SectionName = {}
		PcdName = {}
		ParsedSection = ["LibraryClasses", "Guids", "Ppis", "Protocols"]
		with open(File, 'r') as F:
			for num, value in enumerate(F):
				name = SectionRE.findall(value)
				if name:
					if (name[0] in ParsedSection) or "Pcd" in name[0] or "Guids" in name[0]:
						SectionName[num] = name[0]
						ParseFlag = True
						continue
					else:
						ParseFlag = False
				if ParseFlag == True:
					if value.strip().startswith("#"):
						CommentsFlag = True
					else:
						CommentsFlag = False
					if CommentsFlag:
						comment.append(num)
					if not (value.strip().startswith("#")):
						comment.append(num)
						if not value == "\n":
							pcd = self._split(value)
							PcdName[num] = pcd
							Comments[pcd] = comment
							comment = []
		return SectionName, PcdName,Comments

	#Split the statement in Dec and Inf to get the PcdName
	def _split(self,value):
		return value.replace(' ','').split('=')[0].split('|')[0].split('#')[0].strip()

	def FindFileByExtendName(self,ExtendName,Path):
		Files = []
		for root, dirs, files in os.walk(Path, topdown=True, followlinks=False):
			for name in files:
				if os.path.splitext(name)[-1].lower() == '.%s'%ExtendName:
					FullPath = os.path.join(root,name)
					Files.append(FullPath)
		return Files

	#Find all Inf file in the path to generate the pcd name
	def FindInf(self):
		InfList=self.FindFileByExtendName("inf",self.Path)
		return InfList

	def ParseDec(self):
		Section, Pcd,Comments = self.ParseContent(self.Dec)
		return Section, Pcd, Comments

	def ParseInfFile(self):
		INF_Dict ={}
		for inf in self.FindInf():
			tmp_Section,tmp_Pcd,tmp_Comments = self.ParseContent(inf)
			INF_Dict[inf] = tmp_Section,tmp_Pcd
		return INF_Dict

	#Compare the Pcd name in Dec and Pcd name in Inf, if not equal, save the
	#Pcd name, the Line number, and it's comments
	def CheckPcd(self):
		unuse ={}
		DecSection, DecPcdName,DecComments = self.ParseDec()
		InfsDict = self.ParseInfFile()
		print("DEC File:%s"%self.Dec)
		print("Line Number     Unused PcdName")
		self.Log.append("DEC File:%s\nLine Number     Unused PcdName\n"%self.Dec)
		for LineNum in list(DecPcdName.keys()):
			DPName = DecPcdName[LineNum]
			MatchFlag = False
			for Inf in InfsDict:
				Inf_dict = InfsDict[Inf]
				Inf_section_dict, InfPcdName_dict = Inf_dict
				for key in InfPcdName_dict.keys():
					InfPcdName = InfPcdName_dict[key]
					if DPName in InfPcdName:
						MatchFlag = True
			if MatchFlag == False:
				unuse[LineNum] = DPName
				print("%s%s%s"%("{:>6}".format(LineNum+1)," "*12,DPName))
				self.Log.append("%s%s%s\n"%("{:>6}".format(LineNum+1)," "*12,DPName))
		self.Log.append("\n")
		return unuse,DecComments

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
		with open(self.Dec, 'w+') as T:
			for linenum in range(len(lines)):
				if linenum in removednum:
					continue
				else:
					T.write(lines[linenum])
		print("New Dec File Name:%s, origin Dec File Name:%s.bak"%(self.Dec,self.Dec))

#Function for Write log to log file.
def WriteLog(FileName,content,Flag):
	if Flag == True:
		with open(FileName, 'w+') as log:
			for line in content:
				log.write(line)
	else:
		with open(FileName, 'a+') as log:
			for line in content:
				log.write(line)
	print("Log file Name:%s"%FileName)
	log.close()

def mainprocess(PATH,Flag):
	LogFileFlag = True
	DecPathDict ={}
	for path in PATH:
		decfile = {}
		for root, dirs, files in os.walk(path, topdown=True, followlinks=False):
			for name in files:
				if os.path.splitext(name)[-1].lower() == ".dec":
					file = os.path.join(root, name)
					DecPathDict[file] = root
					decfile[file] = root
		if decfile == {}:
			print("ERROR: No Dec File Found in path %s"%path)
		for i in list(decfile.keys()):
			tmp ={}
			tmp[i] =decfile[i]
			R = PROCESS(tmp)
			unuse,comment = R.CheckPcd()
			WriteLog("Log.txt",R.Log,LogFileFlag)
			LogFileFlag = False
			if Flag:
				R.Clean(unuse,comment)

def main():
	parser = argparse.ArgumentParser(prog=__prog__,
		                                 description=__description__ + __copyright__,
		                                 conflict_handler='resolve')
	parser.add_argument('-v', '--version', action='version', version=__version__,
		                    help="show program's version number and exit")
	parser.add_argument('-i', '--input',metavar="", action = 'append', dest='input', help="Input the package path,e.g. C:\\MyWorkSpace\\Nt32Pkg")
	parser.add_argument('--clean', action = 'store_true', default=False, dest='clean', help="Clean the Unreferenced PCD from DEC file")
	options = parser.parse_args()
	if options.input:
		mainprocess(options.input,options.clean)
	else:
		print("Error: the following argument is required:'-i'")

if __name__ == '__main__':
	main()