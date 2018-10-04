from wonambi.detect import consensus, match_events

rater1 = [
        {'start': 3, 'end': 9, 'chan': 'Cz'},
        {'start': 20, 'end': 25, 'chan': 'Cz'},
        {'start': 30, 'end': 40, 'chan': 'Cz'},
        {'start': 42, 'end': 42.5, 'chan': 'Cz'},
        {'start': 98.1, 'end': 100, 'chan': 'Cz'},
        {'start': 101, 'end': 106, 'chan': 'Cz'},
        {'start': 110.5, 'end': 111, 'chan': 'Cz'},
          ]
rater2 = [
        {'start': 2, 'end': 10, 'chan': 'Cz'},
        {'start': 21, 'end': 26, 'chan': 'Cz'},
        {'start': 39, 'end': 41, 'chan': 'Cz'},
        {'start': 41, 'end': 42, 'chan': 'Cz'},
        {'start': 42, 'end': 42.3, 'chan': 'Cz'},
        {'start': 102, 'end': 105.7, 'chan': 'Cz'},
          ]

def test_agreement_consensus():    
    cons = consensus((rater1, rater2), 1, 512, min_duration=0.5)
    
    assert cons.events == [
            {'start': 3.0, 'end': 9.0, 'chan': 'Cz'},
            {'start': 21.0, 'end': 25.0, 'chan': 'Cz'},
            {'start': 39.0, 'end': 40.0, 'chan': 'Cz'},
            {'start': 102.0, 'end': 105.69921875, 'chan': 'Cz'}]

def test_agreement_match_events():
    match = match_events(rater1, rater2, 0.5)
    
    assert match.precision == 0.5
    assert match.recall == 0.5714285714285714
    assert match.f1score == 0.5333333333333333