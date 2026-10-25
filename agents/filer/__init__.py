"""Filling the student's forms in, showing her the result, and submitting only what she approved.

The loop, and the reason it has the shape it does:

    fill     Every field is computed in code from the student file — her name, her visa, the dates
             on her paystubs, the totals the rules engine wrote. A model never supplies a value on
             a tax form. Each field carries the stored value it came from, so the student (and a
             judge) can see that.

    show     The filled form is rendered to a PDF and left in awaiting_approval. She sees the whole
             document, field by field, before anything happens.

    decide   She approves or declines — in ASI:One, on the dashboard, or out loud on the phone. All
             three land on the same mutation, so there is one place where consent is recorded.

    submit   Only an approved document is ever sent, and only once.

The point of separating show from submit is that these are her tax filings. Docket can do the work
of filling them in; it should not be the thing that decides to file them.
"""
