; QuickText 文本自动输入器 安装包脚本
; 编译：ISCC.exe QuickText.iss  （生成 dist\QuickText_setup.exe）

#define MyAppName "QuickText"
#define MyAppTitle "QuickText 文本自动输入器"
; 版本由 CI 从 git tag 注入：ISCC.exe /DMyAppVersion=0.1.1 QuickText.iss
; 不传则沿用下面这个默认值（应与 quicktext/version.py 保持一致）
#ifndef MyAppVersion
  #define MyAppVersion "0.1.0"
#endif
#define MyAppExe "QuickText.exe"

[Setup]
AppId={{439D9414-D704-440D-B1AB-45D3203ACE65}
AppName={#MyAppTitle}
AppVersion={#MyAppVersion}
AppVerName={#MyAppTitle} {#MyAppVersion}
AppPublisher=QuickText
DefaultDirName={localappdata}\Programs\QuickText
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; 免管理员权限，按当前用户安装（数据保存在 %APPDATA%\QuickText 下）
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=dist
OutputBaseFilename=QuickText_setup_{#MyAppVersion}
SetupIconFile=quicktext\assets\app.ico
UninstallDisplayIcon={app}\{#MyAppExe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
CloseApplicationsFilter={#MyAppExe}
; tag 请保持三段式 x.y.z，这里补齐 Inno 要求的第四段
VersionInfoVersion={#MyAppVersion}.0
VersionInfoProductName={#MyAppTitle}
VersionInfoDescription={#MyAppTitle} 安装程序

[Languages]
Name: "zhcn"; MessagesFile: "tools\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppTitle}"; Filename: "{app}\{#MyAppExe}"
Name: "{group}\卸载 {#MyAppTitle}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppTitle}"; Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "启动 {#MyAppTitle}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  { 移除开机自启项；短语数据保留在 %APPDATA%\QuickText 中 }
  if CurUninstallStep = usUninstall then
  begin
    RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'QuickText');
    RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'QuickText 文本自动输入器');
  end;
end;
