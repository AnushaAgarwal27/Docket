/**
 * Builds Docket's one-minute anonymous survey for international students, as a Google Form in your account.
 * How: https://script.google.com -> New project -> select all, paste this whole file -> Save -> pick makeSurvey
 * -> Run -> allow the permissions. The edit and share links print in the Execution log.
 *
 * Designed for one countable slide number ("X of N didn't know they were exempt"), plus one open box for a
 * quote. Anonymous on purpose: no names, no emails, no pay figures.
 */
function makeSurvey() {
  var form = FormApp.create('International Students: 1-Minute Pay & Tax Survey');
  form.setDescription(
    'For F-1 and J-1 students. Takes about 1 minute, and is anonymous unless you choose to join the waitlist at the end. ' +
    'Answers help the Docket team (Cal Hacks 13.0) show how common these problems are. ' +
    'This survey is not tax or immigration advice.');
  // Anonymous: never collect email addresses, even if the account's Forms default does.
  form.setEmailCollectionType(FormApp.EmailCollectionType.DO_NOT_COLLECT);
  form.setLimitOneResponsePerUser(false); // no sign-in needed, so anyone can answer from their phone
  try {
    form.setRequireLogin(false); // school accounts may limit forms to their own users by default
  } catch (e) {
    // personal Google accounts don't have this setting; the form is already open to everyone
  }

  form.addMultipleChoiceItem().setTitle('Are you on an F-1 or J-1 visa?')
    .setChoiceValues(['Yes, F-1', 'Yes, J-1', 'No']).setRequired(true);

  form.addMultipleChoiceItem().setTitle('Do you work, or have you worked, on campus?')
    .setChoiceValues(['Yes', 'No']).setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('Did you know most F-1 students are exempt from Social Security and Medicare tax for their first 5 years?')
    .setChoiceValues(['Yes', 'No', 'Not sure']).setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('Have you ever checked a paystub to see if Social Security or Medicare was withheld?')
    .setChoiceValues(['Yes', 'No']).setRequired(true);

  form.addMultipleChoiceItem().setTitle('Did you file Form 8843 last year?')
    .setChoiceValues(['Yes', 'No', "Didn't know I had to"]).setRequired(true);

  // Options drawn from university international-office tax and scam guidance; "Other" lets students type their own.
  form.addCheckboxItem()
    .setTitle('Have you ever had any of these legal or financial issues as an F-1 or J-1 student?')
    .setHelpText('Pick all that apply. If none of these fit, choose "Other" and tell us what happened (or type "None").')
    .setChoiceValues([
      'Social Security or Medicare was taken from my paycheck',
      "I didn't know I had to file Form 8843",
      'I filed the wrong tax return (for example a 1040 through TurboTax instead of a 1040-NR)',
      "I missed a tax treaty benefit or didn't understand Form 1042-S or scholarship taxes",
      'I got a scam call or message pretending to be the IRS, Social Security, USCIS or police',
      "An employer paid me late, didn't pay me, or didn't give me a W-2",
      'I worried I worked more than 20 hours a week on campus, or did work my visa may not allow',
      'I had problems with CPT or OPT paperwork, or the OPT unemployment limit',
      'I had trouble getting a Social Security number',
      'I had trouble opening a bank account or building credit (apartment, phone plan, credit card)',
      'I paid high fees or a bad exchange rate sending or receiving money from home'
    ])
    .showOtherOption(true)
    .setRequired(true);

  form.addParagraphTextItem()
    .setTitle('Tell us more about what happened')
    .setHelpText('Optional. We may quote this in our presentation, without any name.');

  // Optional waitlist at the end, so there is only one form. Skipping it keeps the response anonymous.
  form.addSectionHeaderItem().setTitle('Join the Docket waitlist (optional)')
    .setHelpText("Leave your name and email and we'll tell you when Docket launches. Skip this to stay anonymous.");
  form.addTextItem().setTitle('Name (optional)');
  form.addTextItem().setTitle('Email (optional)')
    .setValidation(FormApp.createTextValidation()
      .setHelpText('Please enter a valid email address.')
      .requireTextIsEmail()
      .build());

  form.setConfirmationMessage(
    'Thanks for helping! Most F-1 and J-1 students are exempt from Social Security and Medicare for their first ' +
    '5 calendar years, so check your paystub and confirm with your international student office.');

  Logger.log('Edit the form: ' + form.getEditUrl());
  Logger.log('Share this link: ' + form.getPublishedUrl());
}
