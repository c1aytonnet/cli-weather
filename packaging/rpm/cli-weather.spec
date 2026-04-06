Name:           cli-weather
Version:        0.6.0
Release:        1%{?dist}
Summary:        CLI weather reports and scheduled email delivery
License:        MIT
BuildArch:      noarch
Requires:       python3 >= 3.9

%description
A Python command line weather app with current conditions, 7-day forecasts,
SMTP email delivery, and optional scheduling support.

%prep

%build

%install
mkdir -p %{buildroot}/opt/cli-weather
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/share/doc/cli-weather
cp -R %{project_root}/src %{buildroot}/opt/cli-weather/src
find %{buildroot}/opt/cli-weather/src -type d -name '__pycache__' -prune -exec rm -rf {} +
find %{buildroot}/opt/cli-weather/src -type f -name '*.pyc' -delete
cp %{project_root}/README.md %{buildroot}/usr/share/doc/cli-weather/README.md
cp %{project_root}/LICENSE %{buildroot}/usr/share/doc/cli-weather/LICENSE
install -m 0755 %{project_root}/packaging/bin/cli-weather %{buildroot}/usr/bin/cli-weather

%files
/opt/cli-weather/src
/usr/bin/cli-weather
/usr/share/doc/cli-weather/README.md
/usr/share/doc/cli-weather/LICENSE

%changelog
* Mon Apr 06 2026 Codex - 0.6.0-1
- Initial package release.
