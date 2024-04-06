"""Datebase model for use by SQLAlchemy."""
import json
import re

from typing import List
from typing import Optional

from sqlalchemy import and_
from sqlalchemy import case
from sqlalchemy import null
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy import Integer
from sqlalchemy.ext.hybrid import hybrid_property

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declared_attr
from sqlalchemy.orm import object_session
from sqlalchemy.sql import func

from tools.cache_load import load_cf_set, load_idioms_set
from tools.link_generator import generate_link
from tools.pali_sort_key import pali_sort_key
from tools.pos import CONJUGATIONS
from tools.pos import DECLENSIONS
from tools.pos import EXCLUDE_FROM_FREQ

from dps.tools.sbs_table_functions import SBS_table_tools


class Base(DeclarativeBase):
    pass


class DbInfo(Base):
    """Storing general key-value data such as dpd_release_version and cached
    values, e.g. cf_set and so on."""
    __tablename__ = "db_info"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(unique=True)
    value: Mapped[str] = mapped_column(default='')


class InflectionTemplates(Base):
    __tablename__ = "inflection_templates"

    pattern: Mapped[str] = mapped_column(primary_key=True)
    like: Mapped[str] = mapped_column(default='')
    data: Mapped[str] = mapped_column(default='')

    # infletcion templates pack unpack
    def inflection_template_pack(self, list: list[str]) -> None:
        self.data = json.dumps(list, ensure_ascii=False)

    @property
    def inflection_template_unpack(self) -> list[str]:
        return json.loads(self.data)

    def __repr__(self) -> str:
        return f"InflectionTemplates: {self.pattern} {self.like} {self.data}"


class DpdRoots(Base):
    __tablename__ = "dpd_roots"

    root: Mapped[str] = mapped_column(primary_key=True)
    root_in_comps: Mapped[str] = mapped_column(default='')
    root_has_verb: Mapped[str] = mapped_column(default='')
    root_group: Mapped[int] = mapped_column(default=0)
    root_sign: Mapped[str] = mapped_column(default='')
    root_meaning: Mapped[str] = mapped_column(default='')
    sanskrit_root: Mapped[str] = mapped_column(default='')
    sanskrit_root_meaning: Mapped[str] = mapped_column(default='')
    sanskrit_root_class: Mapped[str] = mapped_column(default='')
    root_example: Mapped[str] = mapped_column(default='')
    dhatupatha_num: Mapped[str] = mapped_column(default='')
    dhatupatha_root: Mapped[str] = mapped_column(default='')
    dhatupatha_pali: Mapped[str] = mapped_column(default='')
    dhatupatha_english: Mapped[str] = mapped_column(default='')
    dhatumanjusa_num: Mapped[int] = mapped_column(default=0)
    dhatumanjusa_root: Mapped[str] = mapped_column(default='')
    dhatumanjusa_pali: Mapped[str] = mapped_column(default='')
    dhatumanjusa_english: Mapped[str] = mapped_column(default='')
    dhatumala_root: Mapped[str] = mapped_column(default='')
    dhatumala_pali: Mapped[str] = mapped_column(default='')
    dhatumala_english: Mapped[str] = mapped_column(default='')
    panini_root: Mapped[str] = mapped_column(default='')
    panini_sanskrit: Mapped[str] = mapped_column(default='')
    panini_english: Mapped[str] = mapped_column(default='')
    note: Mapped[str] = mapped_column(default='')
    matrix_test: Mapped[str] = mapped_column(default='')
    root_info: Mapped[str] = mapped_column(default='')
    root_matrix: Mapped[str] = mapped_column(default='')

    root_ru_meaning: Mapped[str] = mapped_column(default='')
    sanskrit_root_ru_meaning: Mapped[str] = mapped_column(default='')

    created_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now())

    pw: Mapped[List["DpdHeadwords"]] = relationship(
        back_populates="rt")

    @property
    def root_clean(self) -> str:
        """Remove digits from the end"""
        return re.sub(r" \d.*$", "", self.root)

    @property
    def root_no_sign(self) -> str:
        """Remove digits from the end and root sign"""
        return re.sub(r"\d| |√", "", self.root)

    @property
    def root_(self) -> str:
        return self.root.replace(" ", "_")

    @property
    def root_link(self) -> str:
        return self.root.replace(" ", "%20")

    @property
    def root_count(self) -> int:
        db_session = object_session(self)
        if db_session is None:
            raise Exception("No db_session")

        return db_session \
            .query(DpdHeadwords) \
            .filter(DpdHeadwords.root_key == self.root) \
            .count()

    @property
    def root_family_list(self) -> list:
        db_session = object_session(self)
        if db_session is None:
            raise Exception("No db_session")

        results = db_session \
            .query(DpdHeadwords) \
            .filter(DpdHeadwords.root_key == self.root) \
            .group_by(DpdHeadwords.family_root) \
            .all()
        family_list = [i.family_root for i in results if i.family_root is not None]
        family_list = sorted(family_list, key=lambda x: pali_sort_key(x))
        return family_list

    def __repr__(self) -> str:
        return f"""DpdRoots: {self.root} {self.root_group} {self.root_sign} ({self.root_meaning})"""


class FamilyRoot(Base):
    __tablename__ = "family_root"
    root_family_key: Mapped[str] = mapped_column(primary_key=True)
    root_key: Mapped[str] = mapped_column(primary_key=True)
    root_family: Mapped[str] = mapped_column(default='')
    root_meaning: Mapped[str] = mapped_column(default='')
    html: Mapped[str] = mapped_column(default='')
    data: Mapped[str] = mapped_column(default='')
    count: Mapped[int] = mapped_column(default=0)
    html_ru: Mapped[str] = mapped_column(default='')

    __table_args__ = (
        ForeignKeyConstraint(
            ["root_key", "root_family"],
            ["dpd_headwords.root_key", "dpd_headwords.family_root"]
        ),
    )

    # root family pack unpack
    def data_pack(self, list: list[str]) -> None:
        self.data = json.dumps(list, ensure_ascii=False, indent=1)

    @property
    def data_unpack(self) -> list[str]:
        return json.loads(self.data)

    @property
    def root_family_link(self) -> str:
        return self.root_family.replace(" ", "%20")

    @property
    def root_family_(self) -> str:
        return self.root_family.replace(" ", "_")

    @property
    def root_family_clean(self) -> str:
        """Remove root sign"""
        return self.root_family.replace("√", "")

    @property
    def root_family_clean_no_space(self) -> str:
        """Remove root sign and space"""
        return self.root_family.replace("√", "").replace(" ", "")

    def __repr__(self) -> str:
        return f"FamilyRoot: {self.root_family_key} {self.count}"


class Lookup(Base):
    __tablename__ = "lookup"

    lookup_key: Mapped[str] = mapped_column(primary_key=True)
    headwords: Mapped[str] = mapped_column(default='')
    roots: Mapped[str] = mapped_column(default='')
    deconstructor: Mapped[str] = mapped_column(default='')
    variant: Mapped[str] = mapped_column(default='')
    spelling: Mapped[str] = mapped_column(default='')
    grammar: Mapped[str] = mapped_column(default='')
    help: Mapped[str] = mapped_column(default='')
    abbrev: Mapped[str] = mapped_column(default='')
    epd: Mapped[str] = mapped_column(default='')
    other: Mapped[str] = mapped_column(default='')
    sinhala: Mapped[str] = mapped_column(default='')
    devanagari: Mapped[str] = mapped_column(default='')
    thai: Mapped[str] = mapped_column(default='')

    # headwords pack unpack
    
    def headwords_pack(self, list: list[int]) -> None:
        if list:
            self.headwords = json.dumps(list, ensure_ascii=False) 
        else:
            raise ValueError("A list must be provided to pack.")

    @property
    def headwords_unpack(self) -> list[int]:
        if self.headwords:
            return json.loads(self.headwords)
        else:
            return []

    # roots pack unpack
    
    def roots_pack(self, list: list[str]) -> None:
        if list:
            self.roots = json.dumps(list, ensure_ascii=False)
        else:
            raise ValueError("A list must be provided to pack.")

    @property
    def roots_unpack(self) -> list[str]:
        if self.roots:
            return json.loads(self.roots)
        else:
            return []

    # deconstructor pack unpack
    
    def deconstructor_pack(self, list: list[str]) -> None:
        if list:
            self.deconstructor = json.dumps(list, ensure_ascii=False)
        else:
            raise ValueError("A list must be provided to pack.")

    @property
    def deconstructor_unpack(self) -> list[str]:
        if self.deconstructor:
            return json.loads(self.deconstructor)
        else:
            return []

    # variants pack unpack
    
    def variants_pack(self, list: list[str]) -> None:
        if list:
            self.variant = json.dumps(list, ensure_ascii=False)
        else:
            raise ValueError("A list must be provided to pack.")

    @property
    def variants_unpack(self) -> list[str]:
        if self.variant:
            return json.loads(self.variant)
        else:
            return []

    # spelling pack unpack
    
    def spelling_pack(self, list: list[str]) -> None:
        if list:
            self.spelling = json.dumps(list, ensure_ascii=False)
        else:
            raise ValueError("A list must be provided to pack.")

    @property
    def spelling_unpack(self) -> list[str]:
        if self.spelling:
            return json.loads(self.spelling)
        else:
            return []
    
    # grammar pack unpack
    # TODO add a method to unpack to html

    def grammar_pack(self, list: list[tuple[str]]) -> None:
        if list:
            self.grammar = json.dumps(list, ensure_ascii=False)
        else:
            raise ValueError("A list must be provided to pack.")

    @property
    def grammar_unpack(self) -> list[str]:
        if self.grammar:
            return json.loads(self.grammar)
        else:
            return []


    # help pack unpack

    def help_pack(self, string: str) -> None:
        if string:
            self.help = json.dumps(
                string, ensure_ascii=False)
        else:
            raise ValueError("A string must be provided to pack.")

    @property
    def help_unpack(self) -> str:
        if self.help:
            return json.loads(self.help)
        else:
            return ""

    # abbreviations pack unpack

    def abbrev_pack(self, dict: dict[str, str]) -> None:
        if dict:
            self.abbrev = json.dumps(
                dict, ensure_ascii=False, indent=1)
        else:
            raise ValueError("A dict must be provided to pack.")

    @property
    def abbrev_unpack(self) -> dict[str, str]:
        if self.abbrev:
            return json.loads(self.abbrev)
        else:
            return {}

    # pack unpack sinhala
    
    def sinhala_pack(self, list: list[str]) -> None:
        if list:
            self.sinhala = json.dumps(list, ensure_ascii=False)
        else:
            raise ValueError("A list must be provided to pack.")

    @property
    def sinhala_unpack(self) -> list[str]:
        if self.sinhala:
            return json.loads(self.sinhala)
        else:
            return []

    # pack unpack devanagari

    def devanagari_pack(self, list: list[str]) -> None:
        if list:
            self.devanagari = json.dumps(list, ensure_ascii=False)
        else:
            raise ValueError("A list must be provided to pack.")

    @property
    def devanagari_unpack(self) -> list[str]:
        if self.devanagari:
            return json.loads(self.devanagari)
        else:
            return []

    # pack unpack thai

    def thai_pack(self, list: list[str]) -> None:
        if list:
            self.thai = json.dumps(list, ensure_ascii=False)
        else:
            raise ValueError("A list must be provided to pack.")

    @property
    def thai_unpack(self) -> list[str]:
        if self.thai:
            return json.loads(self.thai)
        else:
            return []


    def __repr__(self) -> str:
        return f"""
key:           {self.lookup_key}
headwords:     {self.headwords}
roots:         {self.roots}
deconstructor: {self.deconstructor}
variant:       {self.variant}
spelling:      {self.spelling}
grammar:       {self.grammar}
help:          {self.help}
abbrev:        {self.abbrev}
sinhala:       {self.sinhala}
devanagari:    {self.devanagari}
thai:          {self.thai}
"""


# class PaliWord(Base):
#     """DO NOT USE !!! JUST FOR CONVERTING OLD FILE FORMATS !!!"""
#     __tablename__ = "pali_words"

#     id: Mapped[int] = mapped_column(primary_key=True)
#     pali_1: Mapped[str] = mapped_column(unique=True)
#     pali_2: Mapped[str] = mapped_column(default='')
#     pos: Mapped[str] = mapped_column(default='')
#     grammar: Mapped[str] = mapped_column(default='')
#     derived_from: Mapped[str] = mapped_column(default='')
#     neg: Mapped[str] = mapped_column(default='')
#     verb: Mapped[str] = mapped_column(default='')
#     trans:  Mapped[str] = mapped_column(default='')
#     plus_case:  Mapped[str] = mapped_column(default='')

#     meaning_1: Mapped[str] = mapped_column(default='')
#     meaning_lit: Mapped[str] = mapped_column(default='')
#     meaning_2: Mapped[str] = mapped_column(default='')

#     non_ia: Mapped[str] = mapped_column(default='')
#     sanskrit: Mapped[str] = mapped_column(default='')

#     root_key: Mapped[str] = mapped_column(default='')
#     root_sign: Mapped[str] = mapped_column(default='')
#     root_base: Mapped[str] = mapped_column(default='')

#     family_root: Mapped[str] = mapped_column(default='')
#     family_word: Mapped[str] = mapped_column(default='')
#     family_compound: Mapped[str] = mapped_column(default='')
#     family_set: Mapped[str] = mapped_column(default='')

#     construction:  Mapped[str] = mapped_column(default='')
#     derivative: Mapped[str] = mapped_column(default='')
#     suffix: Mapped[str] = mapped_column(default='')
#     phonetic: Mapped[str] = mapped_column(default='')
#     compound_type: Mapped[str] = mapped_column(default='')
#     compound_construction: Mapped[str] = mapped_column(default='')
#     non_root_in_comps: Mapped[str] = mapped_column(default='')

#     source_1: Mapped[str] = mapped_column(default='')
#     sutta_1: Mapped[str] = mapped_column(default='')
#     example_1: Mapped[str] = mapped_column(default='')

#     source_2: Mapped[str] = mapped_column(default='')
#     sutta_2: Mapped[str] = mapped_column(default='')
#     example_2: Mapped[str] = mapped_column(default='')

#     antonym: Mapped[str] = mapped_column(default='')
#     synonym: Mapped[str] = mapped_column(default='')
#     variant: Mapped[str] = mapped_column(default='')
#     commentary: Mapped[str] = mapped_column(default='')
#     notes: Mapped[str] = mapped_column(default='')
#     cognate: Mapped[str] = mapped_column(default='')
#     link: Mapped[str] = mapped_column(default='')
#     origin: Mapped[str] = mapped_column(default='')

#     stem: Mapped[str] = mapped_column(default='')
#     pattern: Mapped[str] = mapped_column(default='')

#     created_at: Mapped[Optional[DateTime]] = mapped_column(
#         DateTime(timezone=True), server_default=func.now())
#     updated_at: Mapped[Optional[DateTime]] = mapped_column(
#         DateTime(timezone=True), onupdate=func.now())


class DpdHeadwords(Base):
    __tablename__ = "dpd_headwords"

    id: Mapped[int] = mapped_column(primary_key=True)
    lemma_1: Mapped[str] = mapped_column(unique=True)
    lemma_2: Mapped[str] = mapped_column(default='')
    pos: Mapped[str] = mapped_column(default='')
    grammar: Mapped[str] = mapped_column(default='')
    derived_from: Mapped[str] = mapped_column(default='')
    neg: Mapped[str] = mapped_column(default='')
    verb: Mapped[str] = mapped_column(default='')
    trans:  Mapped[str] = mapped_column(default='')
    plus_case:  Mapped[str] = mapped_column(default='')

    meaning_1: Mapped[str] = mapped_column(default='')
    meaning_lit: Mapped[str] = mapped_column(default='')
    meaning_2: Mapped[str] = mapped_column(default='')

    non_ia: Mapped[str] = mapped_column(default='')
    sanskrit: Mapped[str] = mapped_column(default='')

    root_key: Mapped[str] = mapped_column(
        ForeignKey("dpd_roots.root"), default='')
    root_sign: Mapped[str] = mapped_column(default='')
    root_base: Mapped[str] = mapped_column(default='')

    family_root: Mapped[str] = mapped_column(default='')
    family_word: Mapped[str] = mapped_column(
        ForeignKey("family_word.word_family"), default='')
    family_compound: Mapped[str] = mapped_column(default='')
    family_idioms: Mapped[str] = mapped_column(default='')
    family_set: Mapped[str] = mapped_column(default='')

    construction:  Mapped[str] = mapped_column(default='')
    derivative: Mapped[str] = mapped_column(default='')
    suffix: Mapped[str] = mapped_column(default='')
    phonetic: Mapped[str] = mapped_column(default='')
    compound_type: Mapped[str] = mapped_column(default='')
    compound_construction: Mapped[str] = mapped_column(default='')
    non_root_in_comps: Mapped[str] = mapped_column(default='')

    source_1: Mapped[str] = mapped_column(default='')
    sutta_1: Mapped[str] = mapped_column(default='')
    example_1: Mapped[str] = mapped_column(default='')

    source_2: Mapped[str] = mapped_column(default='')
    sutta_2: Mapped[str] = mapped_column(default='')
    example_2: Mapped[str] = mapped_column(default='')

    antonym: Mapped[str] = mapped_column(default='')
    synonym: Mapped[str] = mapped_column(default='')
    variant: Mapped[str] = mapped_column(default='')
    var_phonetic: Mapped[str] = mapped_column(default='')
    var_text: Mapped[str] = mapped_column(default='')
    commentary: Mapped[str] = mapped_column(default='')
    notes: Mapped[str] = mapped_column(default='')
    cognate: Mapped[str] = mapped_column(default='')
    link: Mapped[str] = mapped_column(default='')
    origin: Mapped[str] = mapped_column(default='')

    stem: Mapped[str] = mapped_column(default='')
    pattern: Mapped[str] = mapped_column(
        ForeignKey("inflection_templates.pattern"), default='')

    created_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now())
    
    # derived data 

    inflections: Mapped[str] = mapped_column(default='')
    inflections_sinhala: Mapped[str] = mapped_column(default='')
    inflections_devanagari: Mapped[str] = mapped_column(default='')
    inflections_thai: Mapped[str] = mapped_column(default='')
    inflections_html: Mapped[str] = mapped_column(default='')
    freq_html: Mapped[str] = mapped_column(default='')
    ebt_count: Mapped[int] = mapped_column(default='')

    # pali_root
    rt: Mapped[DpdRoots] = relationship(uselist=False)

    # family_root
    fr = relationship(
        FamilyRoot, 
        primaryjoin=and_(
            root_key==FamilyRoot.root_key, 
            family_root==FamilyRoot.root_family),
        uselist=False 
    )

    #  FamilyWord
    fw = relationship("FamilyWord", uselist=False)

    # sbs
    sbs = relationship("SBS", uselist=False)

    # russion
    ru = relationship("Russian", uselist=False)

    # inflection templates
    it: Mapped[InflectionTemplates] = relationship()


    @hybrid_property
    def root_family_key(self): #type:ignore
        if self.root_key and self.family_root:
            return f"{self.root_key} {self.family_root}"
        else:
            return ""

    @root_family_key.expression
    def root_family_key(cls):
        return case(
            (and_(cls.root_key != null(), cls.family_root != null()), #type:ignore
                 cls.root_key + ' ' + cls.family_root), else_="")    
    
    @property
    def lemma_1_(self) -> str:
        return self.lemma_1.replace(" ", "_").replace(".", "_")

    @property
    def lemma_link(self) -> str:
        return self.lemma_1.replace(" ", "%20")

    @property
    def lemma_clean(self) -> str:
        return re.sub(r" \d.*$", "", self.lemma_1)

    @property
    def root_clean(self) -> str:
        try:
            if self.root_key is None:
                return ""
            else:
                return re.sub(r" \d.*$", "", self.root_key)
        except Exception as e:
            print(f"{self.lemma_1}: {e}")
            return ""
    
    @property
    def construction_line1(self) -> str:
        if self.construction:
            return re.sub("\n.*", "", self.construction)
        else:
            return ""

    @property
    def family_compound_list(self) -> list:
        if self.family_compound:
            return self.family_compound.split(" ")
        else:
            return [self.family_compound]

    @property
    def family_idioms_list(self) -> list:
        if self.family_idioms:
            return self.family_idioms.split(" ")
        else:
            return [self.family_idioms]

    @property
    def family_set_list(self) -> list:
        if self.family_set:
            return self.family_set.split("; ")
        else:
            return [self.family_set]

    @property
    def root_count(self) -> int:
        db_session = object_session(self)
        if db_session is None:
            raise Exception("No db_session")

        return db_session\
            .query(DpdHeadwords.id)\
            .filter(DpdHeadwords\
            .root_key == self.root_key)\
            .count()

    @property
    def pos_list(self) -> list:
        db_session = object_session(self)
        if db_session is None:
            raise Exception("No db_session")

        pos_db = db_session \
            .query(DpdHeadwords.pos) \
            .group_by(DpdHeadwords.pos) \
            .all()
        return sorted([i.pos for i in pos_db])

    @property
    def antonym_list(self) -> list:
        if self.antonym:
            return self.antonym.split(", ")
        else:
            return [self.antonym]

    @property
    def synonym_list(self) -> list:
        if self.synonym:
            return self.synonym.split(", ")
        else:
            return [self.synonym]

    @property
    def variant_list(self) -> list:
        if self.variant:
            return self.variant.split(", ")
        else:
            return [self.variant]

    @property
    def source_link_1(self) -> str:
        return generate_link(self.source_1) if self.source_1 else ""

    @property
    def source_link_2(self) -> str:
        return generate_link(self.source_2) if self.source_2 else ""

    @property
    def source_link_sutta(self) -> str:
        if self.meaning_2:
            if (
                self.family_set.startswith("suttas of") or 
                self.family_set == "bhikkhupātimokkha rules" or 
                self.family_set == "chapters of the Saṃyutta Nikāya"
            ):
                unified_pattern = r"\(([A-Z]+)\s?([\d\.]+)(-\d+)?\)|([A-Z]+)[\s]?([\d\.]+)(-\d+)?"
                match = re.finditer(unified_pattern, self.meaning_2)
                    
                for m in match:
                    prefix = m.group(1) if m.group(1) else m.group(3)
                    number = m.group(2) if m.group(2) else m.group(4)
                    
                    combined_number = f"{prefix}{number}" if prefix and number else None
                    
                    if combined_number:
                        link = generate_link(combined_number)

                        if link:
                            return link

            return ""
        else:
            return ""
    
    @property
    def sanskrit_clean(self) -> str:
        sanskrit_clean = re.sub(r"\[.+\]", "", self.sanskrit)
        return sanskrit_clean.strip()

    # derived data properties

    @property
    def inflections_list(self) -> list:
        if self.inflections:
            return self.inflections.split(",")
        else:
            return []

    @property
    def inflections_sinhala_list(self) -> list:
        if self.inflections_sinhala:
            return self.inflections_sinhala.split(",")
        else:
            return []

    @property
    def inflections_devanagari_list(self) -> list:
        if self.inflections_devanagari:
            return self.inflections_devanagari.split(",")
        else:
            return []

    @property
    def inflections_thai_list(self) -> list:
        if self.inflections_thai:
            return self.inflections_thai.split(",")
        else:
            return []

    # needs_button

    @property
    def needs_grammar_button(self) -> bool:
        return bool(self.meaning_1)

    @property
    def needs_example_button(self) -> bool:
        return bool(
            self.meaning_1 
            and self.example_1 
            and not self.example_2)

    @property
    def needs_examples_button(self) -> bool:
        return bool(
            self.meaning_1 
            and self.example_1 
            and self.example_2)

    @property
    def needs_conjugation_button(self) -> bool:
        return bool(self.pos in CONJUGATIONS)
    
    @property
    def needs_declension_button(self) -> bool:
        return bool(self.pos in DECLENSIONS)

    @property
    def needs_root_family_button(self) -> bool:
        return bool(self.family_root)
    
    @property
    def needs_word_family_button(self) -> bool:
        return bool(self.family_word)

    @property
    def cf_set(self) -> set[str]:
        return load_cf_set()

    @property
    def idioms_set(self) -> set[str]:
        return load_idioms_set( )
    
    @property
    def needs_compound_family_button(self) -> bool:
        return bool(
            self.meaning_1
            and " " not in self.family_compound
            and "sandhi" not in self.pos
            and "idiom" not in self.pos
            and(
                any(item in self.cf_set for item in self.family_compound_list) or
                self.lemma_clean in self.cf_set #type:ignore
            ))

        # alternative logix
        # i.meaning_1
        # and i.lemma_clean in cf_set) 
        # or (
        #     i.meaning_1
        #     and i.family_compound
        #     and any(item in cf_set 
        #         for item in i.family_compound_list))

    @property
    def needs_compound_families_button(self) -> bool:
        return bool(
            self.meaning_1
            and " " in self.family_compound
            and "sandhi" not in self.pos
            and "idiom" not in self.pos
            and(
                any(item in self.cf_set for item in self.family_compound_list)
                or self.lemma_clean in self.cf_set)) #type:ignore

    @property
    def needs_idioms_button(self) -> bool:
        return bool(
            self.meaning_1
            and(
                any(item in self.idioms_set for item in self.family_idioms_list) or
                self.lemma_clean in self.idioms_set #type:ignore
            ))

    # alternative logix
    # if ((i.meaning_1 and i.lemma_clean in idioms_set) 
    #     or (i.family_idioms and any(item in idioms_set 
    #             for item in i.family_idioms_list)))

    @property
    def needs_set_button(self) -> bool:
        return bool(
            self.meaning_1
            and self.family_set
            and len(self.family_set_list) == 1)

    @property
    def needs_sets_button(self) -> bool:
        return bool(
            self.meaning_1
            and self.family_set
            and len(self.family_set_list) > 1)

    @property
    def needs_frequency_button(self) -> bool:
        return bool(self.pos not in EXCLUDE_FROM_FREQ)

    def __repr__(self) -> str:
        return f"""DpdHeadwords: {self.id} {self.lemma_1} {self.pos} {
            self.meaning_1}"""


class FamilyCompound(Base):
    __tablename__ = "family_compound"
    compound_family: Mapped[str] = mapped_column(primary_key=True)
    html: Mapped[str] = mapped_column(default='')
    data: Mapped[str] = mapped_column(default='')
    count: Mapped[int] = mapped_column(default=0)
    html_ru: Mapped[str] = mapped_column(default='')

    # family_compound pack unpack
    def data_pack(self, list: list[str]) -> None:
        self.data = json.dumps(list, ensure_ascii=False, indent=1)

    @property
    def data_unpack(self) -> list[str]:
        return json.loads(self.data)

    def __repr__(self) -> str:
        return f"FamilyCompound: {self.compound_family} {self.count}"


class FamilyWord(Base):
    __tablename__ = "family_word"
    word_family: Mapped[str] = mapped_column(primary_key=True)
    html: Mapped[str] = mapped_column(default='')
    data: Mapped[str] = mapped_column(default='')
    count: Mapped[int] = mapped_column(default=0)
    html_ru: Mapped[str] = mapped_column(default='')

    dpd_headwords: Mapped[List["DpdHeadwords"]] = relationship("DpdHeadwords", back_populates="fw")


    def __repr__(self) -> str:
        return f"FamilyWord: {self.word_family} {self.count}"


class FamilySet(Base):
    __tablename__ = "family_set"
    set: Mapped[str] = mapped_column(primary_key=True)
    html: Mapped[str] = mapped_column(default='')
    data: Mapped[str] = mapped_column(default='')
    count: Mapped[int] = mapped_column(default=0)
    set_ru: Mapped[str] = mapped_column(default='')
    html_ru: Mapped[str] = mapped_column(default='')

    # family_set pack unpack
    def data_pack(self, list: list[str]) -> None:
        self.data = json.dumps(list, ensure_ascii=False, indent=1)

    @property
    def data_unpack(self) -> list[str]:
        return json.loads(self.data)

    def __repr__(self) -> str:
        return f"FamilySet: {self.set} {self.count}"


class FamilyIdiom(Base):
    __tablename__ = "family_idiom"
    idiom: Mapped[str] = mapped_column(primary_key=True)
    html: Mapped[str] = mapped_column(default='')
    data: Mapped[str] = mapped_column(default='')
    count: Mapped[int] = mapped_column(default=0)
    html_ru: Mapped[str] = mapped_column(default='')

    # idioms data pack unpack
    def data_pack(self, list: list[str]) -> None:
        self.data = json.dumps(list, ensure_ascii=False, indent=1)

    @property
    def unpack_idioms_data(self) -> list[str]:
        return json.loads(self.data)

    def __repr__(self) -> str:
        return f"FamilyIdiom: {self.idiom} {self.count}"


class SBS(Base):
    __tablename__ = "sbs"

    id: Mapped[int] = mapped_column(
        ForeignKey('dpd_headwords.id'), primary_key=True)
    sbs_class_anki: Mapped[int] = mapped_column(default='')
    sbs_class: Mapped[int] = mapped_column(default='')
    sbs_category: Mapped[str] = mapped_column(default='')
    sbs_meaning: Mapped[str] = mapped_column(default='')
    sbs_notes: Mapped[str] = mapped_column(default='')
    sbs_source_1: Mapped[str] = mapped_column(default='')
    sbs_sutta_1: Mapped[str] = mapped_column(default='')
    sbs_example_1: Mapped[str] = mapped_column(default='')
    sbs_chant_pali_1: Mapped[str] = mapped_column(default='')
    sbs_chant_eng_1: Mapped[str] = mapped_column(default='')
    sbs_chapter_1: Mapped[str] = mapped_column(default='')
    sbs_source_2: Mapped[str] = mapped_column(default='')
    sbs_sutta_2: Mapped[str] = mapped_column(default='')
    sbs_example_2: Mapped[str] = mapped_column(default='')
    sbs_chant_pali_2: Mapped[str] = mapped_column(default='')
    sbs_chant_eng_2: Mapped[str] = mapped_column(default='')
    sbs_chapter_2: Mapped[str] = mapped_column(default='')
    sbs_source_3: Mapped[str] = mapped_column(default='')
    sbs_sutta_3: Mapped[str] = mapped_column(default='')
    sbs_example_3: Mapped[str] = mapped_column(default='')
    sbs_chant_pali_3: Mapped[str] = mapped_column(default='')
    sbs_chant_eng_3: Mapped[str] = mapped_column(default='')
    sbs_chapter_3: Mapped[str] = mapped_column(default='')
    sbs_source_4: Mapped[str] = mapped_column(default='')
    sbs_sutta_4: Mapped[str] = mapped_column(default='')
    sbs_example_4: Mapped[str] = mapped_column(default='')
    sbs_chant_pali_4: Mapped[str] = mapped_column(default='')
    sbs_chant_eng_4: Mapped[str] = mapped_column(default='')
    sbs_chapter_4: Mapped[str] = mapped_column(default='')


    @declared_attr
    def sbs_index(cls):
        return Column(Integer)

    def calculate_index(self):
        chant_index_map = SBS_table_tools().load_chant_index_map()
        chants = [self.sbs_chant_pali_1, self.sbs_chant_pali_2, self.sbs_chant_pali_3, self.sbs_chant_pali_4]

        indexes = [chant_index_map.get(chant) for chant in chants if chant in chant_index_map]
        indexes = [index for index in indexes if index is not None]  # Filter out None values

        if indexes:
            return min(indexes)
        else:
            return ""


    @property
    def needs_sbs_example_button(self) -> bool:
        count = sum(1 for i in range(1, 5) if getattr(self, f'sbs_example_{i}', '') and getattr(self, f'sbs_example_{i}').strip())
        return count == 1

    @property
    def needs_sbs_examples_button(self) -> bool:
        count = sum(1 for i in range(1, 5) if getattr(self, f'sbs_example_{i}', '') and getattr(self, f'sbs_example_{i}').strip())
        return count >= 2

    # Properties for sbs_chant_link_X
    @property
    def sbs_chant_link_1(self):
        chant_link_map = SBS_table_tools().load_chant_link_map()
        return chant_link_map.get(self.sbs_chant_pali_1, "")

    @property
    def sbs_chant_link_2(self):
        chant_link_map = SBS_table_tools().load_chant_link_map()
        return chant_link_map.get(self.sbs_chant_pali_2, "")

    @property
    def sbs_chant_link_3(self):
        chant_link_map = SBS_table_tools().load_chant_link_map()
        return chant_link_map.get(self.sbs_chant_pali_3, "")

    @property
    def sbs_chant_link_4(self):
        chant_link_map = SBS_table_tools().load_chant_link_map()
        return chant_link_map.get(self.sbs_chant_pali_4, "")

    @property
    def sbs_class_link(self):
        class_link_map = SBS_table_tools().load_class_link_map()
        return class_link_map.get(self.sbs_class_anki, "")

    @property
    def sbs_sutta_link(self):
        sutta_link_map = SBS_table_tools().load_sutta_link_map()
        return sutta_link_map.get(self.sbs_category, "")
    
    @property
    def sbs_source_link_1(self) -> str:
        return generate_link(self.sbs_source_1) if self.sbs_source_1 else ""

    @property
    def sbs_source_link_2(self) -> str:
        return generate_link(self.sbs_source_2) if self.sbs_source_2 else ""

    @property
    def sbs_source_link_3(self) -> str:
        return generate_link(self.sbs_source_3) if self.sbs_source_3 else ""

    @property
    def sbs_source_link_4(self) -> str:
        return generate_link(self.sbs_source_4) if self.sbs_source_4 else ""


    def __repr__(self) -> str:
        return f"SBS: {self.id} {self.sbs_chant_pali_1} {self.sbs_class}"

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sbs_index = self.calculate_index()


class Russian(Base):
    __tablename__ = "russian"

    id: Mapped[int] = mapped_column(
        ForeignKey('dpd_headwords.id'), primary_key=True)
    ru_meaning: Mapped[str] = mapped_column(default="")
    ru_meaning_raw: Mapped[str] = mapped_column(default="")
    ru_meaning_lit: Mapped[str] = mapped_column(default="")
    ru_notes: Mapped[str] = mapped_column(default='')

    def __repr__(self) -> str:
        return f"Russian: {self.id} {self.ru_meaning}"


class BoldDefintion(Base):
    __tablename__ = "bold_defintions"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_name: Mapped[str] = mapped_column(default='')
    ref_code: Mapped[str] = mapped_column(default='')
    nikaya: Mapped[str] = mapped_column(default='')
    book: Mapped[str] = mapped_column(default='')
    title: Mapped[str] = mapped_column(default='')
    subhead: Mapped[str] = mapped_column(default='')
    bold: Mapped[str] = mapped_column(default='')
    bold_end: Mapped[str] = mapped_column(default='')
    commentary: Mapped[str] = mapped_column(default='')

    def update_bold_defintion(
        self, file_name, ref_code, nikaya, book, title, subhead,
			bold, bold_end, commentary):
        self.file_name = file_name
        self.ref_code = ref_code
        self.nikaya = nikaya
        self.book = book
        self.title = title
        self.subhead = subhead
        self.bold = bold
        self.bold_end = bold_end
        self.commentary = commentary


    def __repr__(self) -> str:
        return f"""
{'file_name':<20}{self.file_name}
{'ref_code':<20}{self.ref_code}
{'nikaya':<20}{self.nikaya}
{'book':<20}{self.book}
{'title':<20}{self.title}
{'subhead':<20}{self.subhead}
{'bold':<20}{self.bold}
{'bold_end':<20}{self.bold_end}
{'commentary':<20}{self.commentary}
"""