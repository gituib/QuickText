; QuickText 文本自动输入器 安装包脚本
; 编译：ISCC.exe QuickText.iss  （生成 dist\QuickText_setup.exe）

#define MyAppName "QuickText"
#define MyAppTitle "QuickText 文本自动输入器"
; 版本由 CI 从 quicktext/version.py 读取后注入：ISCC.exe /DMyAppVersion=0.1.2 QuickText.iss
; 不传则沿用下面这个默认值（应与 quicktext/version.py 保持一致）
#ifndef MyAppVersion
  #define MyAppVersion "0.1.2"
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
; 免管理员权限，按当前用户安装（数据保存在安装目录的 data 子目录下）
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

; 不用 UninstallDelete 整目录删除 {app}：个人数据就在 {app}\data 里，
; 删不删由卸载时的勾选框决定；其余程序文件由卸载清单自行清理。

[Code]
const
  { 安装目录下的数据子目录，需与 quicktext\winapi.py 中 config_dir() 保持一致 }
  DataSubDir = 'data';
  { 旧版本存放在 %APPDATA% 下的数据目录，升级安装后可能仍有残留 }
  LegacyDataSubDir = 'QuickText\AutoTyper';

function InitializeSetup(): Boolean;
begin
  Result := True;
end;

{ 程序常驻托盘 + 全局热键，卸载时往往仍在运行。Inno 的 CloseApplications 只在安装阶段生效， }
{ 卸载阶段无法关闭应用，被占用的 QuickText.exe 会被删除失败并残留（需重启才清理，实际常被跳过）。 }
{ 因此卸载开始前主动结束进程：/F /IM 按映像名匹配，onefile 的引导父进程与子进程都会被终止； }
{ 进程不存在时 taskkill 返回失败即可忽略。交互与静默卸载都会走到这里。 }
function InitializeUninstall(): Boolean;
var
  RC: Integer;
begin
  Result := True;
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM "{#MyAppExe}"', '', SW_HIDE,
    ewWaitUntilTerminated, RC);
  { 稍候，确保系统释放文件句柄 }
  Sleep(300);
end;

{ 卸载时展示「清理个人数据」勾选框，返回用户是否勾选。PathList 为已发现的数据目录（每行一个）。 }
{ 只放在卸载确认之后调用：此处无法再中止卸载，因此只有一个「继续卸载」按钮。 }
function AskCleanUserData(const PathList: String): Boolean;
var
  Form: TSetupForm;
  HeadText: TNewStaticText;
  PathText: TNewStaticText;
  CleanCheck: TNewCheckBox;
  NoteText: TNewStaticText;
  OkButton: TNewButton;
begin
  Result := False;
  { CreateCustomForm 的四参数写法需要 Inno Setup 6.6+（CI 用的是最新版 6.x） }
  { 后两个参数 True/True：不随 WizardSizePercent 缩放，保持固定尺寸 }
  Form := CreateCustomForm(520, 208, True, True);
  try
    Form.Caption := ExpandConstant('{#MyAppTitle} 卸载');

    HeadText := TNewStaticText.Create(Form);
    HeadText.Parent := Form;
    HeadText.Left := ScaleX(16);
    HeadText.Top := ScaleY(14);
    HeadText.Caption := '卸载程序发现了保存着您个人数据的目录：';

    PathText := TNewStaticText.Create(Form);
    PathText.Parent := Form;
    PathText.Left := ScaleX(16);
    PathText.Top := ScaleY(38);
    PathText.Caption := PathList;

    CleanCheck := TNewCheckBox.Create(Form);
    CleanCheck.Parent := Form;
    CleanCheck.Left := ScaleX(16);
    CleanCheck.Top := ScaleY(80);
    CleanCheck.Width := Form.ClientWidth - ScaleX(32);
    CleanCheck.Height := ScaleY(17);
    { 默认不勾选：与「保留数据以便日后重装」的既有约定一致 }
    CleanCheck.Checked := False;
    CleanCheck.Caption := '删除上述数据目录（全部短语、快捷键、设置与应用索引）';

    NoteText := TNewStaticText.Create(Form);
    NoteText.Parent := Form;
    NoteText.Left := ScaleX(34);
    NoteText.Top := ScaleY(110);
    NoteText.Caption :=
      '目录中可能包含账号、密码等敏感信息。' + #13#10 +
      '勾选后数据将被永久删除，此操作不可恢复；如需留存，请先在程序内用「导出」备份。' + #13#10 +
      '不勾选则保留该目录，以后重新安装仍可继续使用（推荐）。';

    OkButton := TNewButton.Create(Form);
    OkButton.Parent := Form;
    OkButton.Caption := '继续卸载';
    OkButton.Width := ScaleX(100);
    OkButton.Height := ScaleY(23);
    OkButton.Left := Form.ClientWidth - OkButton.Width - ScaleX(16);
    OkButton.Top := Form.ClientHeight - OkButton.Height - ScaleY(14);
    OkButton.ModalResult := mrOk;
    OkButton.Default := True;
    Form.ActiveControl := OkButton;

    if Form.ShowModal() = mrOk then
      Result := CleanCheck.Checked;
  finally
    Form.Free();
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Dirs: array[0..1] of String;
  PathList: String;
  Found: Integer;
  I: Integer;
  CleanData: Boolean;
begin
  if CurUninstallStep = usUninstall then
  begin
    { 移除开机自启项 }
    RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'QuickText');
    RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'QuickText 文本自动输入器');

    { 数据默认随程序装在应用目录的 data 子目录；旧版本留在 %APPDATA% 的目录一并纳入选择 }
    Dirs[0] := ExpandConstant('{app}\' + DataSubDir);
    Dirs[1] := ExpandConstant('{userappdata}\' + LegacyDataSubDir);
    Found := 0;
    PathList := '';
    for I := 0 to 1 do
      if DirExists(Dirs[I]) then
      begin
        Found := Found + 1;
        if PathList <> '' then
          PathList := PathList + #13#10;
        PathList := PathList + Dirs[I];
      end;

    if Found > 0 then
    begin
      { 静默卸载不弹勾选框，同样保留数据，不阻塞无人值守执行 }
      { 注意：卸载阶段不能调用 WizardSilent，会直接运行期报错 }
      if UninstallSilent then
        CleanData := False
      else
        CleanData := AskCleanUserData(PathList);

      if CleanData then
      begin
        for I := 0 to 1 do
        begin
          if DirExists(Dirs[I]) then
          begin
            if not DelTree(Dirs[I], True, True, True) then
              SuppressibleMsgBox(
                '数据目录未能完全删除，可能被其他程序占用。' + #13#10#13#10 +
                '请稍后手动删除该目录：' + #13#10 + Dirs[I],
                mbInformation, MB_OK, IDOK);
          end;
        end;
        { 数据删干净后顺带移除已空的旧版上级目录；应用目录若已空由卸载程序自行删除 }
        RemoveDir(ExpandConstant('{userappdata}\QuickText'));
      end;
    end;
  end;
end;
