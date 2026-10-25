/**
 * Builds Docket's waitlist sign-up as a Google Form in your account.
 * How: https://script.google.com -> New project -> select all, paste this whole file -> Save -> pick makeWaitlist
 * -> Run -> allow the permissions. The edit and share links print in the Execution log.
 * No sign-in needed to answer: the email is a typed field, not Google's "collect email" setting.
 */
function makeWaitlist() {
  var form = FormApp.create('Join the Docket Waitlist');
  form.setDescription(
    'Docket checks international students\' paychecks for tax taken by mistake, shows the official rule behind ' +
    'every finding, and helps get the money back. Sign up and we\'ll email you when it\'s ready. ' +
    'We only use your email for Docket updates.');
  form.setEmailCollectionType(FormApp.EmailCollectionType.DO_NOT_COLLECT);
  form.setLimitOneResponsePerUser(false);
  try {
    form.setRequireLogin(false); // school accounts may limit forms to their own users by default
  } catch (e) {
    // personal Google accounts don't have this setting
  }

  form.addTextItem().setTitle('Name').setRequired(true);
  form.addTextItem().setTitle('Email').setRequired(true)
    .setValidation(FormApp.createTextValidation()
      .setHelpText('Please enter a valid email address.')
      .requireTextIsEmail()
      .build());
  form.addTextItem().setTitle('School (optional)');
  form.addMultipleChoiceItem().setTitle('Are you on an F-1 or J-1 visa? (optional)')
    .setChoiceValues(['F-1', 'J-1', 'Neither']);

  form.setConfirmationMessage("You're on the list! We'll email you when Docket is ready.");

  Logger.log('Edit the form: ' + form.getEditUrl());
  Logger.log('Share this link: ' + form.getPublishedUrl());
}
