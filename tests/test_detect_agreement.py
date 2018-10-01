from wonambi.detect import consensus

def test_agreement_consensus():
    rater1 = [
            {'start': 3, 'end': 9, 'chan': 'Cz'},
            {'start': 20, 'end': 25, 'chan': 'Cz'},
            {'start': 30, 'end': 40, 'chan': 'Cz'},
            {'start': 42, 'end': 42.5, 'chan': 'Cz'},
              ]
    rater2 = [
            {'start': 2, 'end': 10, 'chan': 'Cz'},
            {'start': 21, 'end': 26, 'chan': 'Cz'},
            {'start': 41, 'end': 42, 'chan': 'Cz'},
            {'start': 42, 'end': 42.3, 'chan': 'Cz'},
              ]
    
    cons = consensus((rater1, rater2), 1, 512, min_duration=0.5)
    
    assert cons.events == [
            {'start': 3.0, 'end': 9.0, 'chan': 'Cz'},
            {'start': 21.0, 'end': 25.0, 'chan': 'Cz'},
              ]

