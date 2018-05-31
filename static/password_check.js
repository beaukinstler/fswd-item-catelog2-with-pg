$(document).ready(function(){
//     function validPassword(){
//         if(password.value==confirm_password.value && password.value != ""){
//         submitButton.disabled = false;
//         message.value = ""
//     }
//     else{
//         submitButton.disabled = true;
//         message.value = "Passwords do not match"

//     }

    
// }
//     var password = document.getElementById("password")
//     var confirm_password = document.getElementById("confirm_password")
//     var submitButton = document.getElementById("submit")
//     var message = document.getElementById("message")

//     // confirm_password.onkeyup = validPassword

$('#password, #confirm_password').on('keyup', function () {
    if ($('#password').val() != "" && $('#password').val() === $('#confirm_password').val()) {
      $('#message').html('Matching').css('color', 'green');
      $('#submit').removeAttr("disabled");
    } else {
      $('#message').html('Not Matching').css('color', 'red');
      $('#submit').attr("disabled", true)}
  });


}) 

