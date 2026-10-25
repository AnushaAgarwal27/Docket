![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

# Docket Filer: fills your forms in, and waits for you to say yes

Form 8843 is due from every F-1 student every year, with or without income, and most students have
never heard of it. This agent fills it in from what is already on your file, shows you the result
field by field, and does nothing else until you approve it. Same for the IRS refund forms when an
employer refuses. It is part of Docket, a caseworker for F-1 international students; students talk
to Docket through the **docket-coordinator** agent in ASI:One.

## Key features
- Every field is computed in code from your stored records; a model never supplies a value on a tax form
- Each field shows the record it came from, so you can check the source of every number
- A missing fact stops the form — it is never filled in with a plausible guess
- Nothing is submitted without your explicit approval, from chat, the dashboard or the phone
- Forms: 8843 (annual statement), 843 (refund claim), 8316 (employer-refused statement), and the written request to your employer

## Usage
Not chatted with directly. Ask **docket-coordinator** in ASI:One; when a form is due it will show
you the filled version and ask. You can also approve on the dashboard or out loud on Docket's phone line.

## Limitations
Docket cannot file with the IRS for you. When you approve an IRS form it is marked signed off and
the PDF is yours to print, sign and mail — the agent says so plainly rather than implying it filed
it. Not tax advice; confirm with your international student office before filing.

## Credits
Built at Cal Hacks 13.0 by Anusha, Rhianna and Soham.
