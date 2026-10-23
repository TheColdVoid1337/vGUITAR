"""Movable guitar voicings and CAGED-derived major/minor scale regions.

Tuning and rows are high E to low E (rows 0..5); emitted steps are bass to
high E. Fingers are only suggestions, not mandatory technique.
"""
from __future__ import annotations

from typing import Sequence

STANDARD_MIDI = (64,59,55,50,45,40)
CAGED_ORDER = ('C','A','G','E','D')
CAGED_BASE_ROOTS = {'C':0,'A':9,'G':7,'E':4,'D':2}
TRIAD_QUALITIES = {'Мажор':(0,4,7), 'Минор':(0,3,7), 'Уменьшённый':(0,3,6)}
TRIAD_LABELS = {'Мажор':('1','3','5'), 'Минор':('1','♭3','5'), 'Уменьшённый':('1','♭3','♭5')}
TRIAD_INVERSIONS = ('Основной вид','1-е обращение','2-е обращение')
TRIAD_STRING_SETS = ((3,2,1), (2,1,0), (4,3,2), (5,4,3))  # bass to treble; 4–3–2, 3–2–1, 5–4–3, 6–5–4
POWER_ROOT_ROWS = (5,4,3)  # strings 6,5,4
POWER_VOICES = ('1–5','1–5–8')

# Fret offsets relative to the nut/capo of each CAGED chord shape.
# Unlike membership-filtered 5-fret windows, each row has an explicit scale
# path associated with the chord family. Rows: thin e, B, G, D, A, thick E.
CAGED_MAJOR_TEMPLATES = {
 'C':((0,1,3),(0,1,3),(0,2,4),(0,2,3),(0,2,3),(0,1,3)),
 'A':((0,2),(0,2,3),(-1,1,2),(-1,0,2),(0,2),(0,2)),
 'G':((0,2,3),(0,1,3),(0,2,4),(0,2,4),(0,2,3),(0,2,3)),
 'E':((-1,0,2),(0,2),(-1,1,2),(-1,1,2),(-1,0,2),(-1,0,2)),
 'D':((0,2,3),(0,2,3),(0,2,4),(0,2,4),(0,2,4),(0,2,3)),
}


def _standard_intervals(tuning: Sequence[int]) -> int:
    if len(tuning)!=6 or any(type(x) is not int for x in tuning):
        raise ValueError('Нужны шесть MIDI-номеров открытых струн')
    offset=tuning[0]-STANDARD_MIDI[0]
    if any(tuning[row]-STANDARD_MIDI[row]!=offset for row in range(6)):
        raise ValueError('Классические формы требуют стандартных интервалов между струнами (Standard / E♭ / D Standard)')
    return offset


def _degree(midi:int, key:int,quality:str) -> str:
    offsets=TRIAD_QUALITIES[quality]
    for interval,label in zip(offsets,TRIAD_LABELS[quality]):
        if (midi-key)%12==interval: return label
    raise ValueError('Нота вне трезвучия')


def caged_scale(tuning: Sequence[int], key:int, form:str, minor:bool=False) -> list[tuple[int,int,int,str]]:
    """5 CAGED-related scale maps, with minor b3/b6/b7 adjustments.

    Numbering uses C-A-G-E-D shape names, not 3NPS positions.
    CAGED minor denotes a minor-scale map around the same root, NOT a
    literal playable minor barre chord for the C and G open-chord grips.
    """
    delta=_standard_intervals(tuning)
    if form not in CAGED_ORDER or not isinstance(key,int) or not 0<=key<12:
        raise ValueError('Неверная CAGED-форма или тональность')
    template=CAGED_MAJOR_TEMPLATES[form]
    start=(key-CAGED_BASE_ROOTS[form]-delta)%12
    # Shift whole pattern by an octave, preserving its shape.
    possible=[start+12*k for k in (-1,0,1,2)]
    def valid_anchor(anchor):
        for row, pair in enumerate(template):
            for offset in pair:
                pitch=tuning[row]+anchor+offset
                rel=(pitch-key)%12
                shift=-1 if minor and rel in (4,9,11) else 0
                if not 0<=anchor+offset+shift<=24:
                    return False
        return True
    possible=[s for s in possible if valid_anchor(s)]
    if not possible: raise ValueError('CAGED-аппликатура не помещается на гриф 0–24')
    start=min(possible,key=lambda s:(abs(s-5),s))
    major_degrees={0:'1',2:'2',4:'3',5:'4',7:'5',9:'6',11:'7'}
    minor_degrees={0:'1',2:'2',3:'♭3',5:'4',7:'5',8:'♭6',10:'♭7'}
    result=[]
    for row in range(5,-1,-1):
        for off in template[row]:
            fret=start+off
            midi=tuning[row]+fret
            rel=(midi-key)%12
            if rel not in major_degrees:
                raise ValueError(f'Invalid CAGED template {form}: string {row+1}, fret {fret}')
            if minor:
                adjustment={4:-1,9:-1,11:-1}.get(rel,0)
                fret+=adjustment;midi+=adjustment
                if fret<0: raise ValueError('Минорная форма выходит за нулевой лад')
            degrees=minor_degrees if minor else major_degrees
            degree=degrees.get((midi-key)%12)
            if degree is None: raise ValueError('Ошибочная ступень CAGED')
            result.append((row,fret,midi,degree))
    if len(set((r,f) for r,f,_,_ in result))!=len(result):
        raise ValueError('Дублирование координат в CAGED-аппликатуре')
    if not any(d=='1' for _,_,_,d in result): raise ValueError('Аппликатура должна содержать тонику')
    return result


def power_chord(tuning:Sequence[int],key:int,root_string:int=6,voice:str='1–5–8') -> list[tuple[int,int,int,str]]:
    """Real adjacent-string power shapes, with octave optional."""
    _standard_intervals(tuning)
    if not 0<=key<12 or root_string not in (4,5,6) or voice not in POWER_VOICES:
        raise ValueError('Неверный параметр power chord')
    # 6th string=5th row, 5th=4th, 4th=3rd
    root_row={6:5,5:4,4:3}[root_string]
    fifth_row=root_row-1
    octave_row=root_row-2
    if octave_row<0:raise ValueError('Нельзя построить октаву на выбранных струнах')
    for fret in range(25):
        if (tuning[root_row]+fret)%12!=key: continue
        root=tuning[root_row]+fret
        fifth_fret=root+7-tuning[fifth_row]
        octave_fret=root+12-tuning[octave_row]
        if 0<=fifth_fret<=24 and 0<=octave_fret<=24 and max(fret,fifth_fret,octave_fret)-min(fret,fifth_fret,octave_fret)<=4:
            out=[(root_row,fret,root,'1'),(fifth_row,fifth_fret,root+7,'5')]
            if voice=='1–5–8':out.append((octave_row,octave_fret,root+12,'8'))
            return out
    raise ValueError('Этот power chord не помещается на доступные лады')


def triad_voicing(tuning:Sequence[int],key:int,quality:str='Мажор',
                  string_set:str='1–2–3', inversion:int=0)->list[tuple[int,int,int,str]]:
    """One close-position triad per inversion on each neighboring string set.

    Inversions enforce the exact *MIDI bass degree*, not an arbitrary
    collection of pitch classes: root, third, fifth in ascending voices.
    """
    _standard_intervals(tuning)
    sets={'1–2–3':(2,1,0),'2–3–4':(3,2,1),'3–4–5':(4,3,2),'4–5–6':(5,4,3)}
    if not 0<=key<12 or quality not in TRIAD_QUALITIES or string_set not in sets or inversion not in (0,1,2):
        raise ValueError('Неверный вид трезвучия, обращение или группа струн')
    offsets=TRIAD_QUALITIES[quality]
    labels=TRIAD_LABELS[quality]
    ordered=list(offsets[inversion:])+[p+12 for p in offsets[:inversion]]
    degrees=list(labels[inversion:])+list(labels[:inversion])
    rows=sets[string_set]
    solutions=[]
    for fret in range(25):
        bass=tuning[rows[0]]+fret
        if (bass-key)%12!=ordered[0]%12:continue
        pitches=[bass]+[bass+(v-ordered[0]) for v in ordered[1:]]
        frets=[p-tuning[r] for p,r in zip(pitches,rows)]
        if any(not 0<=f<=24 for f in frets):continue
        spread=max(frets)-min(frets)
        if spread>5:continue
        # Prefer a playable hand position, with a little space away from the nut.
        solutions.append((spread,abs(min(frets)-5),min(frets),list(zip(rows,frets,pitches,degrees))))
    if not solutions:raise ValueError('Невозможно расположить трезвучие на этой группе струн')
    return min(solutions,key=lambda x:x[:3])[3]


def suggested_fingers(notes:list[tuple[int,int,int,str]]) -> dict[tuple[int,int],str]:
    """Non-authoritative compact position hints; open strings use '0'."""
    if set(d for _r,_f,_m,d in notes).issubset({'1','5','8'}):
        hand={'1':'1','5':'3','8':'4'}
        return {(r,f):('0' if f==0 else hand.get(d, '—')) for r,f,_m,d in notes}
    fretted=sorted({f for _r,f,_m,_d in notes if f>0})
    # If a stretch needs >4 different frets, don't invent an impossible finger.
    rank={f:str(i+1) for i,f in enumerate(fretted)} if len(fretted)<=4 else {}
    return {(r,f):('0' if f==0 else rank.get(f,'—')) for r,f,_,_ in notes}
