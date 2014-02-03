angular.module('groupRoleFormater', []).filter('createNameWithCounter', function() {
	return function(input) {
		var name = '';
		var counter = '';
		if (input.hasOwnProperty("name"))
			name = input.name;
		if (input.hasOwnProperty("counter") && input.counter != undefined)
			counter = ' (' + input.counter + ')';
		return name + counter;
	};
});