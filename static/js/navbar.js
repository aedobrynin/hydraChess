$(document).click(function(event) {
  var width = $(window).width()
  if (width >= 768) return

  var clickover = $(event.target)
  var _opened = $('.navbar-collapse').hasClass('show')
  if (_opened === true && !clickover.hasClass('navbar-toggler')) {
    $('#navbar_toggler').click()
  }
})
