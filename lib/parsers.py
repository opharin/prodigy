#!/usr/bin/env python
#
# This code is part of the binding affinity prediction tools distribution
# and governed by its license.  Please see the LICENSE file that should
# have been included as part of this package.
#

"""
Functions to read PDB/mmCIF files
"""

from __future__ import print_function, division

import os
import sys

try:
    from Bio.PDB import PDBParser, MMCIFParser
    from Bio.PDB.Polypeptide import PPBuilder, is_aa
except ImportError as e:
    print('[!] The binding affinity prediction tools require Biopython', file=sys.stderr)
    raise ImportError(e)



def validate_structure(s, selection=None, prodigy_lig=False):
    # Keep first model only
    if len(s) > 1:
        print('[!] Structure contains more than one model. Only the first one will be kept')
        model_one = s[0].id
        for m in s.child_list[:]:
            if m.id != model_one:
                s.detach_child(m.id)

    # Double occupancy check
    for atom in list(s.get_atoms()):
        if atom.is_disordered():
            residue = atom.parent
            sel_at = atom.selected_child
            sel_at.altloc = ' '
            sel_at.disordered_flag = 0
            residue.detach_child(atom.id)
            residue.add(sel_at)
    if not prodigy_lig:
        # Remove HETATMs and solvent
        res_list = list(s.get_residues())
        _ignore = lambda r: r.id[0][0] == 'W' or r.id[0][0] == 'H'
        for res in res_list:
            if _ignore(res):
                chain = res.parent
                chain.detach_child(res.id)
            elif not is_aa(res, standard=True):
                raise ValueError('Unsupported non-standard amino acid found: {0}'.format(res.resname))

        # Remove Hydrogens
        atom_list = list(s.get_atoms())
        _ignore = lambda x: x.element == 'H'
        for atom in atom_list:
            if _ignore(atom):
                residue = atom.parent
                residue.detach_child(atom.name)

    # Detect gaps and compare with no. of chains
    pep_builder = PPBuilder()
    peptides = pep_builder.build_peptides(s)
    n_peptides = len(peptides)
    chains = list(s.get_chains())
    chain_ids = set([c.id for c in chains])

    if n_peptides != len(chain_ids):
        message= '[!] Structure contains gaps:\n'
        for i_pp, pp in enumerate(peptides):
            message += '\t{1.parent.id} {1.resname}{1.id[1]} < Fragment {0} > ' \
                       '{2.parent.id} {2.resname}{2.id[1]}\n'.format(i_pp, pp[0],pp[-1])
        print(message)
        # raise Exception(message)

    if selection:
        sel_chains=[]
        # Match selected chain with structure
        for sel in selection:
            for c in sel.split(','):
                sel_chains.append(c)
                if c not in chain_ids:
                    raise ValueError('Selected chain not present in provided structure: {0}'.format(c))

        # Remove unselected chains
        _ignore = lambda c: c.id not in sel_chains
        for c in chains:
            if _ignore(c):
                c.parent.detach_child(c.id)

    return s


def parse_structure(path):
    """
    Parses a structure using Biopython's PDB/mmCIF Parser
    Verifies the integrity of the structure (gaps) and its
    suitability for the calculation (is it a complex?).
    """

    print('[+] Reading structure file: {0}'.format(path))
    fname = os.path.basename(path)
    sname = '.'.join(fname.split('.')[:-1])
    s_ext = fname.split('.')[-1]

    _ext = set(('pdb', 'ent', 'cif'))
    if s_ext not in _ext:
        raise IOError('[!] Structure format \'{0}\' is not supported. Use \'.pdb\' or \'.cif\'.'.format(s_ext))

    if s_ext in set(('pdb', 'ent')):
        sparser = PDBParser(QUIET=1)
    elif s_ext == 'cif':
        sparser = MMCIFParser()

    try:
        s = sparser.get_structure(sname, path)
    except Exception as e:
        print('[!] Structure \'{0}\' could not be parsed'.format(sname), file=sys.stderr)
        raise Exception(e)

    return (validate_structure(s),
            len(set([c.id for c in s.get_chains()])),
            len(list(s.get_residues())))