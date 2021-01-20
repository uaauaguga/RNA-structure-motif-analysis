#!/usr/bin/env python
import argparse
import tqdm
import re
import numpy as np
import os 
import sys


def loadPairs(path):
    """Load base pairs and sequence from .ct file"""
    pairs = []
    unpaired = []
    firstLine = True
    sequence = ""
    pairedPos = set()
    with open(path) as f:
        for line in f:
            if firstLine:
                firstLine = False
                continue
            line = line.strip()
            if len(line)==0:
                continue
            fields = re.split(r"\s+",line)
            x,y = int(fields[0]),int(fields[4])
            if y==0:
                unpaired.append(x)
            else:
                pairedPos.add(y)
                if x not in pairedPos:
                    pairs.append((x,y))
            sequence += fields[1] 
    return sequence,pairs,unpaired


def loadFasta(path):
    n = 0
    seq = ""
    with open(path) as f:
        for line in f:
            line = line.strip()
            if len(line)==0:
                continue
            if line.startswith(">"):
                seqid = line.replace(">","").strip()
                n += 1
            else:
                seq += line
    if n != 1:
        print("One and only one sequence should be presented in the input file")
        sys.exit(3)
    return seqid,seq

def adjustPairs(pairs,unpaired,offset):
    adjuated_pairs = []
    adjusted_unpaired = []
    for x,y in pairs:
        x_adjusted = int(x) + int(offset)
        y_adjusted = int(y) + int(offset)
        adjuated_pairs.append((x_adjusted,y_adjusted))
    for ss in unpaired:
        adjusted_unpaired.append(int(ss)+offset)
    return adjuated_pairs,adjusted_unpaired


def checkPairing(seq,pairs):
    canonical = set([("A","U"),("A","T"),
                    ("C","G"),
                    ("G","U"),("G","T"),("G","C"),
                    ("T","A"),("T","G"),
                    ("U","A"),("U","G")])
    pairs_filtered = set()
    n_noncanonical = 0
    for x,y in pairs:
        pair = seq[int(x)-1],seq[int(y)-1]
        if pair  in canonical:
            pairs_filtered.add((x,y))
        else:
            print(x,y,"\t",pair[0],pair[1])
            n_noncanonical += 1
    print("{} non conanical base pairing in the seed structure was removed".format(n_noncanonical))
    return pairs_filtered
        



def makeRNAstructureConstraint(pairs,unpaired):
    """
    Make constrain file in RNA structure" 
    """
    const = ""
    const += "DS:\n-1\n" # No double strand constraint
    const += "SS:\n"     # Single strand constraint
    for ss in unpaired:
        const += "{}\n".format(ss)
    const += "-1\n"
    const += "Mod:\n-1\n"
    const += "Pairs:\n"  # Pairing constraint
    for x,y in pairs:
        const += "{} {}\n".format(x,y)
    const += "-1 -1\n"
    const += "FMN:\n-1\n"
    const += "Forbids:\n-1 -1"
    return const
    
def makeViennaRNAConstraint(pairs,unpaired,length):
    """
    . No constraint
    x Force unpaired
    ( Force left pair
    ) Force right pair
    < Force to be paired, and at left side
    > Force to be paired, and at right side
    """
    const = list(length*".")
    for x,y in pairs:
        x_,y_ = (x-1,y-1) if x < y else (y-1,x-1)
        print(length,x_,y_)
        const[x_] = "("
        const[y_] = ")"
    for ss in unpaired:
        const[ss-1] = "x"
    const_ = ""
    for x in const:
        const_ += x
    return const_


def main():
    #genebank-id:rfam 1based start-end:seed start relative to flanked sequence 0based-end
    parser = argparse.ArgumentParser(description='Prepare constraint file for Fold')
    parser.add_argument('--ct-file','-ct',required=True,help="Ct file of the seed alignment")
    parser.add_argument('--start','-s',required=True,type=int,help="Start of the seed, 0 based relative to sampled sequence")
    parser.add_argument('--end','-e',required=True,type=int,help="End of the seed, 0 based relative to sampled sequence")
    parser.add_argument('--fasta','-fa',required=True,help="Input fasta file for folding")
    parser.add_argument('--format','-f',type=str,default="RNAstructure",choices=["RNAstructure","ViennaRNA"],help="Constraint of the format")
    parser.add_argument('--output','-o',required=True,help="Output constraint file")
    args = parser.parse_args()
    start,end = args.start,args.end
    output = args.output
    offset = start
    seed_length = end - start
    if not os.path.exists(args.ct_file):
        print("Error, {} does not exist.".format(args.ct_file))
        sys.exit(1)
    elif not os.path.exists(args.fasta):
        print("Error, {} does not exist".format(args.fasta))
        sys.exit(1)
    else:
        seqid,full_seq = loadFasta(args.fasta)
        length = len(full_seq)
        seed_seq,pairs,unpaired = loadPairs(args.ct_file)
        pairs = checkPairing(seed_seq,pairs)
        #print(seed_length,len(seed_seq))
        if len(seed_seq)!=seed_length:
            print("Inconsistent seed length for ct file and seed length")
            sys.exit(2)
        #print("Seed:")
        #print(seed_seq)
        #print(full_seq[start:end])
        pairs_adjusted,unpaired_adjusted = adjustPairs(pairs,unpaired,int(offset))
        f = open(output,"w")
        if args.format == "RNAstructure":
            const = makeRNAstructureConstraint(pairs_adjusted,unpaired_adjusted)
            f.write(const+"\n")
        elif args.format=="ViennaRNA":
            const = makeViennaRNAConstraint(pairs_adjusted,unpaired_adjusted,length) 
            f.write(">"+seqid+"\n")
            f.write(full_seq+"\n")
            f.write(const+"\n")
        #print(const)
        f.close()


if __name__ == "__main__":
    main()
