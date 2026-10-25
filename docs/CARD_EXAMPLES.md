# Interactive Card examples

Paste a payload into https://asi1.ai/developer/card-playground to see it rendered. Each card is sent as a
ChatMessage with TextContent (the text above the card) and one MetadataContent holding the metadata below.
Regenerate with `python -m scripts.card_examples`.

## form

Text: Tell me a few facts about your visa and job so I can check your pay.

Payload (`card_payload`):

```json
{
  "title": "Your student profile",
  "fields": [
    {
      "name": "arrival_date",
      "kind": "text",
      "label": "First arrived in the US (YYYY-MM-DD)",
      "required": true
    },
    {
      "name": "visa_type",
      "kind": "select",
      "label": "Visa type",
      "required": true,
      "options": [
        {
          "value": "F-1",
          "label": "F-1"
        },
        {
          "value": "J-1",
          "label": "J-1"
        },
        {
          "value": "other",
          "label": "Other"
        }
      ]
    },
    {
      "name": "employer",
      "kind": "text",
      "label": "On-campus employer",
      "required": true
    },
    {
      "name": "employment_type",
      "kind": "select",
      "label": "How are you paid?",
      "required": true,
      "options": [
        {
          "value": "employee",
          "label": "Employee (W-2, on payroll)"
        },
        {
          "value": "contractor",
          "label": "Contractor (1099)"
        }
      ]
    },
    {
      "name": "employer_is_school",
      "kind": "checkbox",
      "label": "My employer is my school"
    },
    {
      "name": "enrolled",
      "kind": "checkbox",
      "label": "I'm enrolled this term"
    }
  ],
  "submit_cta": {
    "label": "Save profile",
    "selection": {
      "action": "submit_profile"
    }
  }
}
```

Metadata:

```json
{
  "card_protocol_version": "1",
  "requires_card_interaction": "true",
  "card_kind": "form",
  "card_payload": "<payload above, as a JSON string>"
}
```

## detail

Text: The Hearing is over. Here is the verdict.

Payload (`card_payload`):

```json
{
  "title": "Social Security and Medicare withheld",
  "summary_rows": [
    {
      "label": "Social Security",
      "value": "$357.12 \u00b7 high confidence"
    },
    {
      "label": "Medicare",
      "value": "$83.52 \u00b7 medium confidence: an exception may apply"
    },
    {
      "label": "Verdict",
      "value": "Social Security upheld; Medicare downgraded"
    },
    {
      "label": "The rule (IRS Publication 519)",
      "value": "\u201cSocial security and Medicare taxes are not withheld from pay for the work unless the student is considered a resident alien.\u201d"
    }
  ],
  "ctas": [
    {
      "label": "Why? Replay the Hearing",
      "selection": {
        "action": "show_hearing",
        "flag_id": "example_flag_id"
      }
    }
  ]
}
```

Metadata:

```json
{
  "card_protocol_version": "1",
  "requires_card_interaction": "true",
  "card_kind": "detail",
  "card_payload": "<payload above, as a JSON string>"
}
```

## review

Text: Approve and I'll contact payroll; nothing happens until you do.

Payload (`card_payload`):

```json
{
  "title": "Contact payroll about your refund?",
  "summary_rows": [
    {
      "label": "To",
      "value": "University Dining Services payroll"
    },
    {
      "label": "Refund requested",
      "value": "$440.64"
    },
    {
      "label": "Social Security",
      "value": "$357.12"
    },
    {
      "label": "Medicare",
      "value": "$83.52"
    },
    {
      "label": "Hearing verdict",
      "value": "Social Security upheld; Medicare downgraded"
    },
    {
      "label": "How",
      "value": "A call from Docket's AI assistant, which says it is an AI acting with your permission, plus a written request"
    }
  ],
  "approve_cta": {
    "label": "Approve and contact payroll",
    "selection": {
      "action": "approve_refund",
      "case_id": "example_case_id"
    },
    "primary": true
  },
  "reject_cta": {
    "label": "Not now",
    "selection": {
      "action": "decline_refund",
      "case_id": "example_case_id"
    }
  }
}
```

Metadata:

```json
{
  "card_protocol_version": "1",
  "requires_card_interaction": "true",
  "card_kind": "review",
  "card_payload": "<payload above, as a JSON string>"
}
```
